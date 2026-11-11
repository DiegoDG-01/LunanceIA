from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.exc import IntegrityError

from application.auth.config import EmailAuthConfig
from application.auth.dto import ClientContext
from application.auth.services.signups import issue_verification_email
from application.interfaces.email import EmailQueue
from domain.entities.auth.auth_event import AuthAction, AuthEvent
from domain.entities.users.user import User
from domain.repositories.auth.auth_event_repository import AuthEventRepository
from domain.repositories.auth.pending_signup_repository import PendingSignupRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from domain.repositories.users.user_repository import UserRepository
from shared.exceptions.domain import (
    EmailAlreadyExistsError,
    InvalidEmailTokenError,
    UsernameAlreadyExistsError,
)
from shared.utils.emails import normalize_email
from shared.utils.time import utc_now
from shared.utils.tokens import hash_token


@dataclass
class VerifyEmailCommand:
    token: str
    context: ClientContext = field(default_factory=ClientContext)


class VerifyEmailHandler:
    """Abrir el enlace del correo crea la cuenta del registro pendiente, ya verificada, y
    borra el registro con todos sus enlaces: cada enlace sirve una sola vez. No abre sesión:
    después se entra con el correo y la contraseña elegidos al registrarse."""

    def __init__(
        self,
        user_repository: UserRepository,
        pending_signup_repository: PendingSignupRepository,
        auth_event_repository: AuthEventRepository,
        uow: AbstractUnitOfWork,
        now: Callable[[], datetime] = utc_now,
    ):
        self.user_repository = user_repository
        self.pending_signup_repository = pending_signup_repository
        self.auth_event_repository = auth_event_repository
        self.uow = uow
        self._now = now

    async def handle(self, command: VerifyEmailCommand) -> User:
        if not command.token:
            raise InvalidEmailTokenError()
        now = self._now()
        signups = self.pending_signup_repository
        async with self.uow:
            token = await signups.get_token(hash_token(command.token))
            # El lock serializa dos aperturas simultáneas del mismo enlace (o de dos enlaces
            # del mismo registro): la segunda ya no encuentra el registro.
            signup = (
                await signups.get(token.pending_signup_id, for_update=True)
                if token
                else None
            )
            if (
                token is None
                or signup is None
                or signup.id is None
                or not token.is_usable(now)
                or not signup.is_open(now)
            ):
                raise InvalidEmailTokenError()

            if await self.user_repository.get_by_email(signup.email) is not None:
                # El correo consiguió cuenta por otro camino: el registro sobra.
                await signups.delete(signup.id)
                await self.uow.commit()
                raise EmailAlreadyExistsError()

            user = User.create_local_user(
                name=signup.username,
                password=signup.password_hash,
                email=signup.email,
                email_verified=True,
            )
            user.registration_date = now
            try:
                user = await self.user_repository.create(user)
            except IntegrityError:
                await self.uow.rollback()
                taken = True
            else:
                taken = False
                await signups.delete(signup.id)
                await self.auth_event_repository.record(
                    AuthEvent(
                        action=AuthAction.SIGNUP_VERIFIED,
                        created_at=now,
                        user_id=user.id,
                        ip=command.context.ip,
                        user_agent=command.context.user_agent,
                        details={"email": signup.email},
                    )
                )
                await self.uow.commit()

        if taken:
            # Alguien se quedó el username mientras tanto: el registro ya no se puede
            # completar y se libera para que vuelva a registrarse con otro.
            async with self.uow:
                await signups.delete(signup.id)
                await self.uow.commit()
            raise UsernameAlreadyExistsError()
        return user


@dataclass
class ResendVerificationCommand:
    email: str
    context: ClientContext = field(default_factory=ClientContext)


class ResendVerificationHandler:
    """Otro enlace para un registro sin confirmar. Los anteriores siguen valiendo hasta
    caducar. Termina igual exista o no el registro (o la cuenta): no revela nada."""

    def __init__(
        self,
        user_repository: UserRepository,
        pending_signup_repository: PendingSignupRepository,
        auth_event_repository: AuthEventRepository,
        email_queue: EmailQueue,
        config: EmailAuthConfig,
        uow: AbstractUnitOfWork,
        now: Callable[[], datetime] = utc_now,
    ):
        self.user_repository = user_repository
        self.pending_signup_repository = pending_signup_repository
        self.auth_event_repository = auth_event_repository
        self.email_queue = email_queue
        self.config = config
        self.uow = uow
        self._now = now

    async def handle(self, command: ResendVerificationCommand) -> None:
        email = normalize_email(command.email or "")
        if not email:
            return
        now = self._now()
        async with self.uow:
            if await self.user_repository.get_by_email(email) is not None:
                return
            signup = await self.pending_signup_repository.get_by_email(email)
            if signup is None or not signup.is_open(now):
                return
            outgoing = await issue_verification_email(
                self.pending_signup_repository, signup, self.config, now
            )
            await self.auth_event_repository.record(
                AuthEvent(
                    action=AuthAction.SIGNUP_VERIFICATION_RESENT,
                    created_at=now,
                    ip=command.context.ip,
                    user_agent=command.context.user_agent,
                    details={"email": email},
                )
            )
            await self.uow.commit()
        self.email_queue.enqueue(outgoing)
