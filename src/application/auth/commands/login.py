from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import cast

from application.auth.dto import ClientContext, IssuedSession
from application.auth.services.sessions import SessionManager
from application.interfaces.auth_service import PasswordHasher, SessionRevocationList
from domain.entities.auth.auth_event import AuthAction, AuthEvent
from domain.entities.users.user import User
from domain.repositories.auth.auth_event_repository import AuthEventRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from domain.repositories.users.user_repository import UserRepository
from shared.exceptions.application import CommandValidationError
from shared.exceptions.domain import InvalidCredentialsError, UserInactiveError
from shared.utils.time import utc_now


@dataclass
class LoginCommand:
    username: str
    password: str
    context: ClientContext = field(default_factory=ClientContext)


class LoginHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        auth_event_repository: AuthEventRepository,
        session_manager: SessionManager,
        password_hasher: PasswordHasher,
        revocations: SessionRevocationList,
        uow: AbstractUnitOfWork,
        now: Callable[[], datetime] = utc_now,
    ):
        self.user_repository = user_repository
        self.auth_event_repository = auth_event_repository
        self.session_manager = session_manager
        self.password_hasher = password_hasher
        self.revocations = revocations
        self.uow = uow
        self._now = now

    async def handle(self, command: LoginCommand) -> IssuedSession:
        if not command.username or not command.password:
            raise CommandValidationError(
                "LoginCommand", ["Nombre de usuario y contraseña son requeridos"]
            )

        user = await self.user_repository.get_by_username(command.username)

        if user is None or user.password is None:
            await self.password_hasher.verify_dummy(command.password)
            await self._record_failure(command, user, "invalid_credentials")
            raise InvalidCredentialsError("username")

        if not await self.password_hasher.verify(command.password, user.password):
            await self._record_failure(command, user, "invalid_credentials")
            raise InvalidCredentialsError("password")

        # Después de la contraseña: sin ella no se revela que la cuenta está desactivada.
        if not user.is_active:
            await self._record_failure(command, user, "inactive")
            raise UserInactiveError()

        now = self._now()
        async with self.uow:
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
        """`login.throttled`: el rate limit del login cortó la petición."""
        async with self.uow:
            await self.auth_event_repository.record(
                AuthEvent(
                    action=AuthAction.LOGIN_THROTTLED,
                    created_at=self._now(),
                    ip=command.context.ip,
                    user_agent=command.context.user_agent,
                    details={"username": command.username},
                )
            )
            await self.uow.commit()

    async def _record_failure(
        self, command: LoginCommand, user: User | None, reason: str
    ) -> None:
        async with self.uow:
            await self.auth_event_repository.record(
                AuthEvent(
                    action=AuthAction.LOGIN_FAILED,
                    created_at=self._now(),
                    user_id=user.id if user else None,
                    ip=command.context.ip,
                    user_agent=command.context.user_agent,
                    details={"username": command.username, "reason": reason},
                )
            )
            await self.uow.commit()
