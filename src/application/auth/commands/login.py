from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import cast

from application.auth.dto import ClientContext, IssuedSession
from application.auth.services.login_guard import LoginGuard
from application.auth.services.sessions import SessionManager
from application.interfaces.auth_service import PasswordHasher, SessionRevocationList
from domain.entities.auth.auth_event import AuthAction, AuthEvent
from domain.entities.users.user import User
from domain.repositories.auth.auth_event_repository import AuthEventRepository
from domain.repositories.auth.pending_signup_repository import PendingSignupRepository
from domain.repositories.auth.session_repository import SessionRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from domain.repositories.users.user_repository import UserRepository
from shared.exceptions.application import CommandValidationError, TooManyAttemptsError
from shared.exceptions.domain import (
    EmailNotVerifiedError,
    InvalidCredentialsError,
    UserInactiveError,
)
from shared.utils.emails import normalize_email
from shared.utils.time import utc_now


@dataclass
class LoginCommand:
    email: str
    password: str
    context: ClientContext = field(default_factory=ClientContext)


class LoginHandler:
    """Login con correo y contraseña.

    Antes de mirar la contraseña se consultan los bloqueos por intentos fallidos
    (`LoginGuard`); si Redis no responde, el guard lanza 503. La respuesta a un correo
    inexistente, a uno sin contraseña y a una contraseña incorrecta es la misma, con el
    mismo coste de Argon2.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        auth_event_repository: AuthEventRepository,
        session_manager: SessionManager,
        password_hasher: PasswordHasher,
        revocations: SessionRevocationList,
        uow: AbstractUnitOfWork,
        *,
        login_guard: LoginGuard,
        session_repository: SessionRepository,
        pending_signup_repository: PendingSignupRepository,
        now: Callable[[], datetime] = utc_now,
    ):
        self.user_repository = user_repository
        self.auth_event_repository = auth_event_repository
        self.session_manager = session_manager
        self.password_hasher = password_hasher
        self.revocations = revocations
        self.uow = uow
        self.login_guard = login_guard
        self.session_repository = session_repository
        self.pending_signup_repository = pending_signup_repository
        self._now = now

    async def handle(self, command: LoginCommand) -> IssuedSession:
        email = normalize_email(command.email or "")
        if not email or not command.password:
            raise CommandValidationError(
                "LoginCommand", ["Correo y contraseña son requeridos"]
            )
        ip = command.context.ip

        locks = await self.login_guard.locks(email, ip)
        if locks.ip is not None:
            await self._record_throttled(command, email, scope="ip")
            raise TooManyAttemptsError(locks.ip)

        user = await self.user_repository.get_by_email(email)
        if locks.account is not None and not await self._known_device(user, command):
            await self._record_throttled(command, email, scope="account", user=user)
            raise TooManyAttemptsError(locks.account)

        if user is None or user.password is None:
            await self._check_pending_signup(command, email)
            await self.login_guard.record_failure(email, ip)
            await self._record_failure(command, email, user, "invalid_credentials")
            raise InvalidCredentialsError("email")

        if not await self.password_hasher.verify(command.password, user.password):
            await self.login_guard.record_failure(email, ip)
            await self._record_failure(command, email, user, "invalid_credentials")
            raise InvalidCredentialsError("password")

        # Después de la contraseña: sin ella no se revela que la cuenta está desactivada.
        if not user.is_active:
            await self._record_failure(command, email, user, "inactive")
            raise UserInactiveError()

        await self.login_guard.succeeded(email, ip)

        now = self._now()
        async with self.uow:
            # Comparte el lock de la fila con el reset y el cambio de contraseña: una
            # contraseña validada justo antes de cambiarla no abre sesión después de que
            # el cambio cerró las demás.
            locked = await self.user_repository.get_by_id(
                cast(int, user.id), for_update=True
            )
            if locked is None or locked.password != user.password:
                await self.uow.rollback()
                await self._record_failure(command, email, user, "password_changed")
                raise InvalidCredentialsError("password")
            if self.password_hasher.needs_rehash(user.password):
                # bcrypt heredado (o parámetros de Argon2 más débiles): se aprovecha que
                # tenemos la contraseña en claro para guardarla con el hash actual.
                user.password = await self.password_hasher.hash(command.password)
            user.last_login = now
            await self.user_repository.update(user)

            issued, replaced = await self.session_manager.open(
                user_id=cast(int, user.id),
                user_uuid=user.uuid,
                context=command.context,
                now=now,
            )
            await self.auth_event_repository.record(
                AuthEvent(
                    action=AuthAction.LOGIN_SUCCEEDED,
                    created_at=now,
                    user_id=user.id,
                    session_id=issued.session.id,
                    ip=command.context.ip,
                    user_agent=command.context.user_agent,
                    details={
                        "session_uuid": issued.session.uuid,
                        "platform": issued.session.platform.value,
                    },
                )
            )
            await self.uow.commit()

        await self.revocations.revoke([session.uuid for session in replaced])
        return issued

    async def record_throttled(self, command: LoginCommand) -> None:
        """`login.throttled`: el rate limit por IP del endpoint cortó la petición."""
        await self._record_throttled(
            command, normalize_email(command.email or ""), scope="rate_limit"
        )

    async def _known_device(self, user: User | None, command: LoginCommand) -> bool:
        device_id = command.context.device_id
        if user is None or user.id is None or device_id is None:
            return False
        return await self.session_repository.has_device(user.id, device_id)

    async def _check_pending_signup(self, command: LoginCommand, email: str) -> None:
        """Sin cuenta todavía. Si la contraseña es la de un registro pendiente, se avisa de
        que falta confirmar el correo: solo lo sabe quien conoce esa contraseña. Si no, se
        gasta lo mismo que una verificación real para no revelar nada por el tiempo."""
        signup = await self.pending_signup_repository.get_by_email(email)
        if signup is None or not signup.is_open(self._now()):
            await self.password_hasher.verify_dummy(command.password)
            return
        if await self.password_hasher.verify(command.password, signup.password_hash):
            await self._record_failure(command, email, None, "email_not_verified")
            raise EmailNotVerifiedError()

    async def _record_throttled(
        self,
        command: LoginCommand,
        email: str,
        *,
        scope: str,
        user: User | None = None,
    ) -> None:
        async with self.uow:
            await self.auth_event_repository.record(
                AuthEvent(
                    action=AuthAction.LOGIN_THROTTLED,
                    created_at=self._now(),
                    user_id=user.id if user else None,
                    ip=command.context.ip,
                    user_agent=command.context.user_agent,
                    details={"email": email, "scope": scope},
                )
            )
            await self.uow.commit()

    async def _record_failure(
        self, command: LoginCommand, email: str, user: User | None, reason: str
    ) -> None:
        async with self.uow:
            await self.auth_event_repository.record(
                AuthEvent(
                    action=AuthAction.LOGIN_FAILED,
                    created_at=self._now(),
                    user_id=user.id if user else None,
                    ip=command.context.ip,
                    user_agent=command.context.user_agent,
                    details={"email": email, "reason": reason},
                )
            )
            await self.uow.commit()
