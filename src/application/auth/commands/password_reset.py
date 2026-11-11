from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from application.auth.config import EmailAuthConfig
from application.auth.dto import ClientContext
from application.auth.emails import (
    FORGOT_PASSWORD_PATH,
    RESEND_VERIFICATION_PATH,
    RESET_PASSWORD_PATH,
    app_link,
    password_changed,
    password_reset,
    signup_pending_confirmation,
)
from application.auth.services.login_guard import LoginGuard
from application.auth.services.sessions import record_revocation
from application.interfaces.auth_service import PasswordHasher, SessionRevocationList
from application.interfaces.email import EmailQueue, OutgoingEmail
from domain.entities.auth.auth_event import AuthAction, AuthEvent
from domain.entities.auth.password_reset_token import PasswordResetToken
from domain.entities.auth.session import RevocationReason
from domain.repositories.auth.auth_event_repository import AuthEventRepository
from domain.repositories.auth.password_reset_token_repository import (
    PasswordResetTokenRepository,
)
from domain.repositories.auth.pending_signup_repository import PendingSignupRepository
from domain.repositories.auth.session_repository import SessionRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from domain.repositories.users.user_repository import UserRepository
from shared.exceptions.domain import InvalidEmailTokenError
from shared.utils.emails import normalize_email
from shared.utils.time import utc_now
from shared.utils.tokens import generate_token, hash_token
from shared.validators.business import UserValidator


@dataclass
class RequestPasswordResetCommand:
    email: str
    context: ClientContext = field(default_factory=ClientContext)


class RequestPasswordResetHandler:
    """ "Olvidé mi contraseña". Siempre termina sin error: la respuesta (204) no revela si el
    correo tiene cuenta. Los enlaces anteriores siguen valiendo hasta que uno se use: pedir
    otro no deja sin salida a quien abre el primero.

    Un registro sin confirmar recibe en su lugar instrucciones para confirmar el correo.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        pending_signup_repository: PendingSignupRepository,
        reset_token_repository: PasswordResetTokenRepository,
        auth_event_repository: AuthEventRepository,
        email_queue: EmailQueue,
        config: EmailAuthConfig,
        uow: AbstractUnitOfWork,
        now: Callable[[], datetime] = utc_now,
    ):
        self.user_repository = user_repository
        self.pending_signup_repository = pending_signup_repository
        self.reset_token_repository = reset_token_repository
        self.auth_event_repository = auth_event_repository
        self.email_queue = email_queue
        self.config = config
        self.uow = uow
        self._now = now

    async def handle(self, command: RequestPasswordResetCommand) -> None:
        email = normalize_email(command.email or "")
        if not email:
            return
        now = self._now()
        outgoing: OutgoingEmail | None = None
        async with self.uow:
            user = await self.user_repository.get_by_email(email)
            if user is None:
                signup = await self.pending_signup_repository.get_by_email(email)
                if signup is not None and signup.is_open(now):
                    outgoing = signup_pending_confirmation(
                        to=email,
                        resend_link=app_link(
                            self.config.link_base_url, RESEND_VERIFICATION_PATH
                        ),
                    )
            elif user.is_active and user.id is not None:
                token = generate_token()
                await self.reset_token_repository.add(
                    PasswordResetToken(
                        token_hash=hash_token(token),
                        user_id=user.id,
                        created_at=now,
                        expires_at=now + self.config.password_reset_ttl,
                    )
                )
                await self.auth_event_repository.record(
                    AuthEvent(
                        action=AuthAction.PASSWORD_RESET_REQUESTED,
                        created_at=now,
                        user_id=user.id,
                        ip=command.context.ip,
                        user_agent=command.context.user_agent,
                    )
                )
                await self.uow.commit()
                outgoing = password_reset(
                    to=email,
                    username=user.name,
                    link=app_link(
                        self.config.link_base_url, RESET_PASSWORD_PATH, token
                    ),
                    ttl=self.config.password_reset_ttl,
                )
        if outgoing is not None:
            self.email_queue.enqueue(outgoing)


@dataclass
class ResetPasswordCommand:
    token: str
    password: str
    context: ClientContext = field(default_factory=ClientContext)


class ResetPasswordHandler:
    """Cambia la contraseña con el enlace del correo y cierra todas las sesiones de la
    cuenta: si alguien la conocía, pierde el acceso al instante. El enlace sirve una vez y
    deja sin efecto los demás enlaces pendientes."""

    def __init__(
        self,
        user_repository: UserRepository,
        reset_token_repository: PasswordResetTokenRepository,
        session_repository: SessionRepository,
        auth_event_repository: AuthEventRepository,
        password_hasher: PasswordHasher,
        revocations: SessionRevocationList,
        login_guard: LoginGuard,
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
        self.login_guard = login_guard
        self.email_queue = email_queue
        self.config = config
        self.uow = uow
        self._now = now

    async def handle(self, command: ResetPasswordCommand) -> None:
        UserValidator.validate_password(command.password)
        if not command.token:
            raise InvalidEmailTokenError()
        token_hash = hash_token(command.token)

        # El enlace se comprueba antes del trabajo caro: con un token inventado nadie
        # consigue un hash Argon2. Se vuelve a comprobar (y se gasta) con la fila bloqueada.
        stored = await self.reset_token_repository.get(token_hash)
        if stored is None or not stored.is_usable(self._now()):
            raise InvalidEmailTokenError()
        password_hash = await self.password_hasher.hash(command.password)

        async with self.uow:
            # Dos enlaces del mismo usuario no cambian la contraseña a la vez: el primero
            # invalida los demás antes de que el segundo consiga el lock.
            user = await self.user_repository.get_by_id(stored.user_id, for_update=True)
            now = self._now()
            if user is None or user.id is None:
                raise InvalidEmailTokenError()
            if not await self.reset_token_repository.consume(token_hash, now):
                raise InvalidEmailTokenError()
            await self.reset_token_repository.invalidate_for_user(user.id, now)

            user.password = password_hash
            # Abrir el enlace prueba que el correo es suyo.
            user.email_verified = True
            await self.user_repository.update(user)

            revoked = await self.session_repository.revoke_active(
                user.id, now, RevocationReason.PASSWORD_RESET
            )
            for session in revoked:
                await record_revocation(
                    self.auth_event_repository,
                    session,
                    now=now,
                    revoked_by="system",
                    context=command.context,
                )
            await self.auth_event_repository.record(
                AuthEvent(
                    action=AuthAction.PASSWORD_RESET,
                    created_at=now,
                    user_id=user.id,
                    ip=command.context.ip,
                    user_agent=command.context.user_agent,
                    details={"sessions_revoked": len(revoked)},
                )
            )
            await self.uow.commit()

        await self.revocations.revoke([session.uuid for session in revoked])
        if user.email:
            # El dueño ya no debe seguir bloqueado por los intentos de un atacante.
            await self.login_guard.clear_account(user.email)
            self.email_queue.enqueue(
                password_changed(
                    to=user.email,
                    username=user.name,
                    forgot_link=app_link(
                        self.config.link_base_url, FORGOT_PASSWORD_PATH
                    ),
                )
            )
