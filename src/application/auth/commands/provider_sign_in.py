"""Entrar con Google o Apple: misma sesión por dispositivo que el login con contraseña."""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, cast

from application.auth.config import EmailAuthConfig
from application.auth.dto import ClientContext, IssuedSession
from application.auth.emails import FORGOT_PASSWORD_PATH, app_link, provider_linked
from application.auth.services.apple_tokens import AppleTokenVault
from application.auth.services.external_accounts import (
    ConcurrentSignInError,
    ExternalAccount,
    ExternalAccounts,
)
from application.auth.services.sessions import SessionManager
from application.interfaces.auth_service import SessionRevocationList
from application.interfaces.email import EmailQueue
from application.interfaces.identity_providers import (
    AppleSignInGateway,
    AppleTokens,
    IdentityProvider,
    ProviderIdentity,
    UsedProviderTokens,
)
from domain.entities.auth.auth_event import AuthAction, AuthEvent
from domain.entities.users.user import User
from domain.repositories.auth.auth_event_repository import AuthEventRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from domain.repositories.users.user_repository import UserRepository
from shared.exceptions.application import (
    IdentityProviderUnavailableError,
    InvalidProviderTokenError,
    ProviderNotConfiguredError,
    ServiceTemporarilyUnavailableError,
)
from shared.exceptions.domain import (
    ProviderAccountConflictError,
    ProviderLinkRequiredError,
    UserInactiveError,
)
from shared.utils.time import utc_now

logger = logging.getLogger(__name__)

# Dos peticiones con la misma identidad a la vez: la segunda reintenta y encuentra la cuenta.
SIGN_IN_ATTEMPTS = 2


class ProviderVerifier(Protocol):
    async def verify(self, token: str, /, *, nonce: str | None) -> ProviderIdentity: ...


@dataclass
class ProviderSignInCommand:
    provider: IdentityProvider
    id_token: str
    nonce: str | None = None
    # Apple: el código de autorización para obtener su refresh token y el nombre, que Apple
    # solo da a la app la primera vez que el usuario autoriza Lunance.
    authorization_code: str | None = None
    name: str | None = None
    context: ClientContext = field(default_factory=ClientContext)


@dataclass(frozen=True, slots=True)
class ProviderSignInResult:
    issued: IssuedSession
    user: User
    account_created: bool
    provider_linked: bool


class ProviderTokenGate:
    """Verificación común a entrar y vincular: proveedor configurado, token válido, de un solo
    uso y, con Apple, el canje del código de autorización."""

    def __init__(
        self,
        *,
        google: ProviderVerifier | None,
        apple: AppleSignInGateway | None,
        used_tokens: UsedProviderTokens,
    ):
        self.google = google
        self.apple = apple
        self.used_tokens = used_tokens

    def verifier(self, provider: IdentityProvider) -> ProviderVerifier:
        verifier = self.google if provider is IdentityProvider.GOOGLE else self.apple
        if verifier is None:
            raise ProviderNotConfiguredError(provider.label)
        return verifier

    async def verify(
        self, provider: IdentityProvider, token: str, nonce: str | None
    ) -> ProviderIdentity:
        """Lanza `InvalidProviderTokenError` (motivo `replay` si ya se usó)."""
        identity = await self.verifier(provider).verify(token, nonce=nonce)
        # Después de la firma: un token inventado no llega a ocupar Redis.
        if not await self.used_tokens.claim(token, expires_at=identity.expires_at):
            raise InvalidProviderTokenError(provider.value, "replay")
        return identity

    async def exchange_apple_code(
        self, identity: ProviderIdentity, authorization_code: str | None
    ) -> AppleTokens | None:
        """El refresh token de Apple, o None si no hay código o no se puede canjear ahora.

        Un código que Apple rechaza (usado, caducado, de otra app) o que es de otro usuario
        invalida la petición. Si Apple no responde se entra igual: el token se obtendrá en el
        siguiente inicio de sesión."""
        apple = self.apple
        if (
            identity.provider is not IdentityProvider.APPLE
            or not authorization_code
            or apple is None
        ):
            return None
        if not apple.can_exchange_codes:
            logger.warning(
                "Apple code received but APPLE_PRIVATE_KEY is not configured"
            )
            return None
        try:
            tokens = await apple.exchange_code(
                authorization_code, client_id=identity.audience
            )
        except IdentityProviderUnavailableError:
            logger.warning("Apple token endpoint unavailable; signing in without it")
            return None
        if tokens is None:
            raise InvalidProviderTokenError("apple", "authorization_code")
        if tokens.subject is not None and tokens.subject != identity.subject:
            raise InvalidProviderTokenError("apple", "authorization_code_subject")
        return tokens


class ProviderSignInHandler:
    """Verifica el token, encuentra/vincula/crea la cuenta (`ExternalAccounts`) y abre la
    sesión del dispositivo. Al vincular por correo avisa al buzón."""

    def __init__(
        self,
        *,
        gate: ProviderTokenGate,
        accounts: ExternalAccounts,
        user_repository: UserRepository,
        auth_event_repository: AuthEventRepository,
        session_manager: SessionManager,
        revocations: SessionRevocationList,
        email_queue: EmailQueue,
        email_config: EmailAuthConfig,
        uow: AbstractUnitOfWork,
        apple_tokens: AppleTokenVault | None = None,
        now: Callable[[], datetime] = utc_now,
    ):
        self.gate = gate
        self.accounts = accounts
        self.user_repository = user_repository
        self.auth_event_repository = auth_event_repository
        self.session_manager = session_manager
        self.revocations = revocations
        self.email_queue = email_queue
        self.email_config = email_config
        self.uow = uow
        self.apple_tokens = apple_tokens
        self._now = now

    async def handle(self, command: ProviderSignInCommand) -> ProviderSignInResult:
        provider = command.provider
        self.gate.verifier(provider)
        try:
            identity = await self.gate.verify(provider, command.id_token, command.nonce)
            apple_tokens = await self.gate.exchange_apple_code(
                identity, command.authorization_code
            )
        except InvalidProviderTokenError as error:
            if error.reason == "replay":
                await self._record(
                    command,
                    AuthAction.PROVIDER_TOKEN_REPLAY,
                    {"method": provider.value},
                )
            else:
                await self._record_failure(command, error.reason)
            raise

        for attempt in range(SIGN_IN_ATTEMPTS):
            try:
                return await self._sign_in(command, identity, apple_tokens)
            except ConcurrentSignInError:
                await self.uow.rollback()
                if attempt == SIGN_IN_ATTEMPTS - 1:
                    raise ServiceTemporarilyUnavailableError("sign_in", 1) from None
            except InvalidProviderTokenError as error:
                await self._record_failure(command, error.reason, identity)
                raise
            except (ProviderLinkRequiredError, ProviderAccountConflictError) as error:
                reason = (
                    "link_required"
                    if isinstance(error, ProviderLinkRequiredError)
                    else "provider_conflict"
                )
                await self._record_failure(command, reason, identity)
                raise
        raise AssertionError("unreachable")

    async def _sign_in(
        self,
        command: ProviderSignInCommand,
        identity: ProviderIdentity,
        apple_tokens: AppleTokens | None,
    ) -> ProviderSignInResult:
        now = self._now()
        async with self.uow:
            account = await self.accounts.resolve(identity, name=command.name, now=now)
            user_id = cast(int, account.user.id)
            # Con lock, como el login con contraseña: no se cruza con un reset o un cambio.
            user = await self.user_repository.get_by_id(user_id, for_update=True)
            if user is None:
                raise InvalidProviderTokenError(identity.provider.value, "account_gone")
            if not user.is_active:
                await self.uow.rollback()
                await self._record_failure(command, "inactive", identity, user)
                raise UserInactiveError()

            user.last_login = now
            await self.user_repository.update(user)
            if apple_tokens is not None and self.apple_tokens is not None:
                await self.apple_tokens.store(user_id, apple_tokens)

            issued, replaced = await self.session_manager.open(
                user_id=user_id, user_uuid=user.uuid, context=command.context, now=now
            )
            await self._record_account_events(command, account, identity, now)
            await self.auth_event_repository.record(
                AuthEvent(
                    action=AuthAction.LOGIN_SUCCEEDED,
                    created_at=now,
                    user_id=user_id,
                    session_id=issued.session.id,
                    ip=command.context.ip,
                    user_agent=command.context.user_agent,
                    details={
                        "session_uuid": issued.session.uuid,
                        "platform": issued.session.platform.value,
                        "method": identity.provider.value,
                        "account_created": account.created,
                        "provider_linked": account.linked,
                    },
                )
            )
            await self.uow.commit()

        await self.revocations.revoke([session.uuid for session in replaced])
        if account.linked and user.email:
            self.email_queue.enqueue(
                provider_linked(
                    to=user.email,
                    username=user.name,
                    provider=identity.provider.label,
                    automatic=True,
                    forgot_link=app_link(
                        self.email_config.link_base_url, FORGOT_PASSWORD_PATH
                    ),
                )
            )
        return ProviderSignInResult(
            issued=issued,
            user=user,
            account_created=account.created,
            provider_linked=account.linked,
        )

    async def _record_account_events(
        self,
        command: ProviderSignInCommand,
        account: ExternalAccount,
        identity: ProviderIdentity,
        now: datetime,
    ) -> None:
        if account.created:
            await self.auth_event_repository.record(
                AuthEvent(
                    action=AuthAction.SIGNUP_VERIFIED,
                    created_at=now,
                    user_id=account.user.id,
                    ip=command.context.ip,
                    user_agent=command.context.user_agent,
                    details={
                        "email": account.user.email,
                        "method": identity.provider.value,
                    },
                )
            )
        if account.linked:
            await self.auth_event_repository.record(
                AuthEvent(
                    action=AuthAction.PROVIDER_LINKED,
                    created_at=now,
                    user_id=account.user.id,
                    ip=command.context.ip,
                    user_agent=command.context.user_agent,
                    details={"provider": identity.provider.value, "mode": "email"},
                )
            )

    async def _record_failure(
        self,
        command: ProviderSignInCommand,
        reason: str,
        identity: ProviderIdentity | None = None,
        user: User | None = None,
    ) -> None:
        details: dict[str, str] = {"method": command.provider.value, "reason": reason}
        if identity is not None and identity.email:
            details["email"] = identity.email
        await self._record(command, AuthAction.LOGIN_FAILED, details, user)

    async def _record(
        self,
        command: ProviderSignInCommand,
        action: AuthAction,
        details: dict[str, str],
        user: User | None = None,
    ) -> None:
        async with self.uow:
            await self.auth_event_repository.record(
                AuthEvent(
                    action=action,
                    created_at=self._now(),
                    user_id=user.id if user else None,
                    ip=command.context.ip,
                    user_agent=command.context.user_agent,
                    details=details,
                )
            )
            await self.uow.commit()
