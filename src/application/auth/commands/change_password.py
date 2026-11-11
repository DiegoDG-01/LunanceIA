from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from application.auth.config import EmailAuthConfig
from application.auth.dto import ClientContext
from application.auth.emails import FORGOT_PASSWORD_PATH, app_link, password_changed
from application.auth.services.sessions import record_revocation
from application.interfaces.auth_service import PasswordHasher, SessionRevocationList
from application.interfaces.email import EmailQueue
from domain.entities.auth.auth_event import AuthAction, AuthEvent
from domain.entities.auth.session import RevocationReason
from domain.repositories.auth.auth_event_repository import AuthEventRepository
from domain.repositories.auth.password_reset_token_repository import (
    PasswordResetTokenRepository,
)
from domain.repositories.auth.session_repository import SessionRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from domain.repositories.users.user_repository import UserRepository
from shared.exceptions.domain import (
    InvalidCurrentPasswordError,
    PasswordUnchangedError,
    UserNotFoundError,
)
from shared.utils.time import utc_now
from shared.validators.business import UserValidator


@dataclass
class ChangePasswordCommand:
    user_id: int
    # Sesión desde la que se cambia (la del access token): es la única que sigue abierta.
    session_uuid: str
    current_password: str
    new_password: str
    context: ClientContext = field(default_factory=ClientContext)


class ChangePasswordHandler:
    """Cambio de contraseña con sesión iniciada. Pide la actual y cierra las demás sesiones
    (`password_change`); la actual se conserva. También deja sin efecto los enlaces de
    recuperación pendientes."""

    def __init__(
        self,
        user_repository: UserRepository,
        reset_token_repository: PasswordResetTokenRepository,
        session_repository: SessionRepository,
        auth_event_repository: AuthEventRepository,
        password_hasher: PasswordHasher,
        revocations: SessionRevocationList,
        email_queue: EmailQueue,
        config: EmailAuthConfig,
        uow: AbstractUnitOfWork,
        now: Callable[[], datetime] = utc_now,
    ):
        self.user_repository = user_repository
        self.reset_token_repository = reset_token_repository
        self.session_repository = session_repository
        self.auth_event_repository = auth_event_repository
        self.password_hasher = password_hasher
        self.revocations = revocations
        self.email_queue = email_queue
        self.config = config
        self.uow = uow
        self._now = now

    async def handle(self, command: ChangePasswordCommand) -> None:
        user = await self.user_repository.get_by_id(command.user_id)
        if user is None:
            raise UserNotFoundError()
        if user.password is None or not await self.password_hasher.verify(
            command.current_password or "", user.password
        ):
            raise InvalidCurrentPasswordError()
        if command.new_password == command.current_password:
            raise PasswordUnchangedError()
        UserValidator.validate_password(command.new_password)
        password_hash = await self.password_hasher.hash(command.new_password)

        async with self.uow:
            locked = await self.user_repository.get_by_id(
                command.user_id, for_update=True
            )
            # Otra petición la cambió mientras tanto: la "actual" que se comprobó ya no lo es.
            if locked is None or locked.password != user.password:
                raise InvalidCurrentPasswordError()
            now = self._now()
            locked.password = password_hash
            await self.user_repository.update(locked)
            await self.reset_token_repository.invalidate_for_user(command.user_id, now)

            revoked = await self.session_repository.revoke_active(
                command.user_id,
                now,
                RevocationReason.PASSWORD_CHANGE,
                except_uuid=command.session_uuid,
            )
            for session in revoked:
                await record_revocation(
                    self.auth_event_repository,
                    session,
                    now=now,
                    revoked_by="user",
                    context=command.context,
                    actor_session_uuid=command.session_uuid,
                )
            await self.auth_event_repository.record(
                AuthEvent(
                    action=AuthAction.PASSWORD_CHANGED,
                    created_at=now,
                    user_id=command.user_id,
                    ip=command.context.ip,
                    user_agent=command.context.user_agent,
                    details={
                        "session_uuid": command.session_uuid,
                        "sessions_revoked": len(revoked),
                    },
                )
            )
            await self.uow.commit()

        await self.revocations.revoke([session.uuid for session in revoked])
        if locked.email:
            self.email_queue.enqueue(
                password_changed(
                    to=locked.email,
                    username=locked.name,
                    forgot_link=app_link(
                        self.config.link_base_url, FORGOT_PASSWORD_PATH
                    ),
                )
            )
