"""Vincular y desvincular Google o Apple desde una cuenta con sesión iniciada.

Vincular no exige que el correo del proveedor coincida con el de la cuenta: quien tiene la
sesión prueba que la cuenta es suya y el ID token, que la del proveedor también. Se avisa al
correo de la cuenta. Desvincular nunca deja la cuenta sin forma de entrar.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.exc import IntegrityError

from application.auth.commands.provider_sign_in import ProviderTokenGate
from application.auth.config import EmailAuthConfig
from application.auth.dto import ClientContext
from application.auth.emails import (
    FORGOT_PASSWORD_PATH,
    app_link,
    provider_linked,
    provider_unlinked,
)
from application.auth.services.apple_tokens import (
    AppleAuthorizationRevoker,
    AppleTokenVault,
)
from application.auth.services.external_accounts import (
    linked_subject,
    set_subject,
)
from application.interfaces.email import EmailQueue
from application.interfaces.identity_providers import AppleTokens, IdentityProvider
from domain.entities.auth.auth_event import AuthAction, AuthEvent
from domain.entities.users.user import User
from domain.repositories.auth.auth_event_repository import AuthEventRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from domain.repositories.users.user_repository import UserRepository
from shared.exceptions.application import InvalidProviderTokenError
from shared.exceptions.domain import (
    LastLoginMethodError,
    ProviderAccountConflictError,
    ProviderAlreadyLinkedError,
    UserNotFoundError,
)
from shared.utils.time import utc_now


@dataclass
class LinkProviderCommand:
    user_id: int
    session_uuid: str
    provider: IdentityProvider
    id_token: str
    nonce: str | None = None
    authorization_code: str | None = None
    context: ClientContext = field(default_factory=ClientContext)


@dataclass
class UnlinkProviderCommand:
    user_id: int
    session_uuid: str
    provider: IdentityProvider
    context: ClientContext = field(default_factory=ClientContext)


class _ProviderAccountHandler:
    def __init__(
        self,
        *,
        user_repository: UserRepository,
        auth_event_repository: AuthEventRepository,
        email_queue: EmailQueue,
        email_config: EmailAuthConfig,
        uow: AbstractUnitOfWork,
        now: Callable[[], datetime] = utc_now,
    ):
        self.user_repository = user_repository
        self.auth_event_repository = auth_event_repository
        self.email_queue = email_queue
        self.email_config = email_config
        self.uow = uow
        self._now = now

    def _forgot_link(self) -> str:
        return app_link(self.email_config.link_base_url, FORGOT_PASSWORD_PATH)

    async def _record(
        self,
        action: AuthAction,
        user_id: int,
        context: ClientContext,
        details: dict,
        now: datetime,
    ) -> None:
        await self.auth_event_repository.record(
            AuthEvent(
                action=action,
                created_at=now,
                user_id=user_id,
                ip=context.ip,
                user_agent=context.user_agent,
                details=details,
            )
        )


class LinkProviderHandler(_ProviderAccountHandler):
    def __init__(
        self,
        *,
        gate: ProviderTokenGate,
        apple_tokens: AppleTokenVault | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.gate = gate
        self.apple_tokens = apple_tokens

    async def handle(self, command: LinkProviderCommand) -> User:
        provider = command.provider
        try:
            identity = await self.gate.verify(provider, command.id_token, command.nonce)
            apple_tokens = await self.gate.exchange_apple_code(
                identity, command.authorization_code
            )
        except InvalidProviderTokenError as error:
            async with self.uow:
                action = (
                    AuthAction.PROVIDER_TOKEN_REPLAY
                    if error.reason == "replay"
                    else AuthAction.LOGIN_FAILED
                )
                await self._record(
                    action,
                    command.user_id,
                    command.context,
                    {"method": provider.value, "reason": error.reason, "mode": "link"},
                    self._now(),
                )
                await self.uow.commit()
            raise

        now = self._now()
        async with self.uow:
            user = await self.user_repository.get_by_id(
                command.user_id, for_update=True
            )
            if user is None:
                raise UserNotFoundError()
            current = linked_subject(user, provider)
            if current == identity.subject:
                # Ya estaba vinculada: solo se renueva el token de Apple si llegó uno.
                await self._store_apple_tokens(user, apple_tokens)
                await self.uow.commit()
                return user
            if current is not None:
                raise ProviderAccountConflictError(provider.label)
            other = await self._holder(provider, identity.subject)
            if other is not None:
                raise ProviderAlreadyLinkedError(provider.label)

            set_subject(user, provider, identity.subject)
            try:
                user = await self.user_repository.update(user)
            except IntegrityError:
                raise ProviderAlreadyLinkedError(provider.label) from None
            await self._store_apple_tokens(user, apple_tokens)
            await self._record(
                AuthAction.PROVIDER_LINKED,
                command.user_id,
                command.context,
                {
                    "provider": provider.value,
                    "mode": "manual",
                    "session_uuid": command.session_uuid,
                },
                now,
            )
            await self.uow.commit()

        if user.email:
            self.email_queue.enqueue(
                provider_linked(
                    to=user.email,
                    username=user.name,
                    provider=provider.label,
                    automatic=False,
                    forgot_link=self._forgot_link(),
                )
            )
        return user

    async def _holder(self, provider: IdentityProvider, subject: str) -> User | None:
        if provider is IdentityProvider.GOOGLE:
            return await self.user_repository.get_by_google_sub(subject)
        return await self.user_repository.get_by_apple_sub(subject)

    async def _store_apple_tokens(self, user: User, tokens: AppleTokens | None) -> None:
        if tokens is not None and self.apple_tokens is not None and user.id is not None:
            await self.apple_tokens.store(user.id, tokens)


class UnlinkProviderHandler(_ProviderAccountHandler):
    """Quita el vínculo. Con Apple, además, borra su refresh token y lo revoca en Apple
    (mejor esfuerzo, después del commit). Sin vínculo no hace nada (idempotente)."""

    def __init__(
        self,
        *,
        apple_tokens: AppleTokenVault | None = None,
        apple_revoker: AppleAuthorizationRevoker | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.apple_tokens = apple_tokens
        self.apple_revoker = apple_revoker

    async def handle(self, command: UnlinkProviderCommand) -> User:
        provider = command.provider
        now = self._now()
        revoke: AppleTokens | None = None
        async with self.uow:
            user = await self.user_repository.get_by_id(
                command.user_id, for_update=True
            )
            if user is None:
                raise UserNotFoundError()
            if linked_subject(user, provider) is None:
                return user
            if [
                method for method in user.login_methods if method != provider.value
            ] == []:
                raise LastLoginMethodError()

            set_subject(user, provider, None)
            user = await self.user_repository.update(user)
            if provider is IdentityProvider.APPLE:
                if self.apple_tokens is not None:
                    revoke = await self.apple_tokens.load(command.user_id)
                await self.user_repository.set_apple_refresh_token(
                    command.user_id, None
                )
            await self._record(
                AuthAction.PROVIDER_UNLINKED,
                command.user_id,
                command.context,
                {"provider": provider.value, "session_uuid": command.session_uuid},
                now,
            )
            await self.uow.commit()

        if revoke is not None and self.apple_revoker is not None:
            await self.apple_revoker.revoke_quietly(revoke)
        if user.email:
            self.email_queue.enqueue(
                provider_unlinked(
                    to=user.email,
                    username=user.name,
                    provider=provider.label,
                    forgot_link=self._forgot_link(),
                )
            )
        return user
