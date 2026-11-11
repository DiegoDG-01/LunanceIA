from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.exc import IntegrityError

from application.auth.config import EmailAuthConfig
from application.auth.dto import ClientContext
from application.auth.emails import (
    FORGOT_PASSWORD_PATH,
    LOGIN_PATH,
    account_already_exists,
    app_link,
)
from application.auth.services.signups import issue_verification_email
from application.interfaces.auth_service import PasswordHasher
from application.interfaces.email import EmailQueue, OutgoingEmail
from domain.entities.auth.auth_event import AuthAction, AuthEvent
from domain.entities.auth.pending_signup import PendingSignup
from domain.repositories.auth.auth_event_repository import AuthEventRepository
from domain.repositories.auth.pending_signup_repository import PendingSignupRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from domain.repositories.users.user_repository import UserRepository
from shared.exceptions.application import CommandValidationError
from shared.exceptions.domain import UsernameAlreadyExistsError
from shared.utils.emails import normalize_email
from shared.utils.time import utc_now
from shared.validators.business import UserValidator


@dataclass
class RegisterCommand:
    """Registro con correo, username y contraseña."""

    email: str
    username: str
    password: str
    context: ClientContext = field(default_factory=ClientContext)


class RegisterHandler:
    """Guarda el registro como pendiente y manda el enlace de verificación; la cuenta se crea
    al abrirlo (`VerifyEmailHandler`).

    La respuesta nunca revela si el correo ya tiene cuenta: en ese caso no se guarda nada y
    al buzón le llega un aviso en lugar del enlace. El hash de la contraseña se calcula
    siempre, para que el tiempo de respuesta tampoco lo delate.

    Volver a registrarse con un correo que tiene un registro pendiente lo sustituye (nuevo
    username y contraseña) e invalida los enlaces anteriores: quien registró primero un correo
    ajeno no se queda con él, y solo vale el último enlace que llegó al buzón.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        pending_signup_repository: PendingSignupRepository,
        auth_event_repository: AuthEventRepository,
        password_hasher: PasswordHasher,
        email_queue: EmailQueue,
        config: EmailAuthConfig,
        uow: AbstractUnitOfWork,
        now: Callable[[], datetime] = utc_now,
    ):
        self.user_repository = user_repository
        self.pending_signup_repository = pending_signup_repository
        self.auth_event_repository = auth_event_repository
        self.password_hasher = password_hasher
        self.email_queue = email_queue
        self.config = config
        self.uow = uow
        self._now = now

    async def handle(self, command: RegisterCommand) -> None:
        email = normalize_email(command.email or "")
        username = (command.username or "").strip()
        if not email:
            raise CommandValidationError("RegisterCommand", ["El correo es requerido"])
        if not username:
            raise CommandValidationError("RegisterCommand", ["El nombre es requerido"])
        UserValidator.validate_password(command.password)

        password_hash = await self.password_hasher.hash(command.password)
        now = self._now()
        try:
            outgoing = await self._register(
                command, email, username, password_hash, now
            )
        except IntegrityError:
            # Otro registro simultáneo ganó la carrera por el correo o por el username.
            if await self._username_reserved_by_other(username, email, now):
                raise UsernameAlreadyExistsError() from None
            return
        self.email_queue.enqueue(outgoing)

    async def _register(
        self,
        command: RegisterCommand,
        email: str,
        username: str,
        password_hash: str,
        now: datetime,
    ) -> OutgoingEmail:
        async with self.uow:
            # El username se revisa antes que el correo: la respuesta por un username ocupado
            # es la misma tenga o no cuenta el correo.
            if await self.user_repository.get_by_username(username) is not None:
                raise UsernameAlreadyExistsError()
            if await self._username_reserved_by_other(username, email, now):
                raise UsernameAlreadyExistsError()

            existing = await self.user_repository.get_by_email(email)
            if existing is not None:
                await self._record(command, email, "existing_account", existing.id, now)
                await self.uow.commit()
                base = self.config.link_base_url
                return account_already_exists(
                    to=email,
                    login_link=app_link(base, LOGIN_PATH),
                    forgot_link=app_link(base, FORGOT_PASSWORD_PATH),
                    login_methods=existing.login_methods,
                )

            signup = await self._save_signup(email, username, password_hash, now)
            outgoing = await issue_verification_email(
                self.pending_signup_repository, signup, self.config, now
            )
            await self._record(command, email, "pending", None, now)
            await self.uow.commit()
        return outgoing

    async def _save_signup(
        self, email: str, username: str, password_hash: str, now: datetime
    ) -> PendingSignup:
        repository = self.pending_signup_repository
        expires_at = now + self.config.pending_signup_ttl
        current = await repository.get_by_email(email, for_update=True)
        if current is not None:
            # Se sustituye (abierto o caducado): solo vale el enlace que se manda ahora.
            await repository.delete_tokens(current.id)  # type: ignore[arg-type]
            await self._release_expired_username(username, email, now)
            current.username = username
            current.password_hash = password_hash
            current.created_at = now
            current.expires_at = expires_at
            await repository.save(current)
            return current

        await self._release_expired_username(username, email, now)
        return await repository.add(
            PendingSignup(
                email=email,
                username=username,
                password_hash=password_hash,
                created_at=now,
                expires_at=expires_at,
            )
        )

    async def _release_expired_username(
        self, username: str, email: str, now: datetime
    ) -> None:
        """Un registro caducado de otro correo deja de reservar el username."""
        holder = await self.pending_signup_repository.get_by_username(username)
        if holder is not None and holder.email != email and not holder.is_open(now):
            await self.pending_signup_repository.delete(holder.id)  # type: ignore[arg-type]

    async def _username_reserved_by_other(
        self, username: str, email: str, now: datetime
    ) -> bool:
        holder = await self.pending_signup_repository.get_by_username(username)
        return holder is not None and holder.email != email and holder.is_open(now)

    async def _record(
        self,
        command: RegisterCommand,
        email: str,
        outcome: str,
        user_id: int | None,
        now: datetime,
    ) -> None:
        await self.auth_event_repository.record(
            AuthEvent(
                action=AuthAction.SIGNUP_REQUESTED,
                created_at=now,
                user_id=user_id,
                ip=command.context.ip,
                user_agent=command.context.user_agent,
                details={"email": email, "outcome": outcome},
            )
        )
