"""Google y Apple: verificadores construidos una vez a partir de `settings` y handlers.

Un proveedor sin client IDs no se construye (None): sus rutas responden
`AUTH_PROVIDER_NOT_CONFIGURED`. Las claves públicas quedan en caché dentro del verificador,
que vive lo que el proceso.
"""

from functools import lru_cache

from fastapi import Depends

from application.auth.commands.apple_notifications import AppleNotificationHandler
from application.auth.commands.change_username import ChangeUsernameHandler
from application.auth.commands.link_provider import (
    LinkProviderHandler,
    UnlinkProviderHandler,
)
from application.auth.commands.provider_sign_in import (
    ProviderSignInHandler,
    ProviderTokenGate,
)
from application.auth.config import EmailAuthConfig
from application.auth.services.apple_tokens import (
    AppleAuthorizationRevoker,
    AppleTokenVault,
)
from application.auth.services.external_accounts import ExternalAccounts
from application.auth.services.sessions import SessionManager
from application.interfaces.auth_service import PasswordHasher, SessionRevocationList
from application.interfaces.email import EmailQueue
from application.interfaces.identity_providers import (
    AppleSignInGateway,
    GoogleTokenVerifier,
    SecretCipher,
    UsedProviderTokens,
)
from domain.repositories.auth.auth_event_repository import AuthEventRepository
from domain.repositories.auth.pending_signup_repository import PendingSignupRepository
from domain.repositories.auth.session_repository import SessionRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from infrastructure.cache.provider_tokens import RedisUsedProviderTokens
from infrastructure.cache.redis import get_redis
from infrastructure.config.settings import settings
from infrastructure.database.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from infrastructure.security.apple_sign_in import AppleSignInClient
from infrastructure.security.google_id_tokens import GoogleIdTokenVerifier
from infrastructure.security.secret_cipher import AesGcmSecretCipher
from presentation.dependencies.auth_handler_deps import get_session_manager
from presentation.dependencies.auth_services import (
    get_email_auth_config,
    get_password_hasher,
    get_session_revocations,
)
from presentation.dependencies.email_deps import get_email_queue
from presentation.dependencies.repositories import (
    get_auth_event_repository,
    get_pending_signup_repository,
    get_session_repository,
    get_unit_of_work_repository,
    get_user_repository,
)


@lru_cache
def get_google_verifier() -> GoogleTokenVerifier | None:
    if not settings.GOOGLE_CLIENT_IDS:
        return None
    return GoogleIdTokenVerifier(client_ids=settings.GOOGLE_CLIENT_IDS)


@lru_cache
def get_apple_gateway() -> AppleSignInGateway | None:
    if not settings.APPLE_CLIENT_IDS:
        return None
    return AppleSignInClient(
        client_ids=settings.APPLE_CLIENT_IDS,
        team_id=settings.APPLE_TEAM_ID,
        key_id=settings.APPLE_KEY_ID,
        private_key_pem=settings.APPLE_PRIVATE_KEY.get_secret_value(),
    )


@lru_cache
def get_apple_token_cipher() -> SecretCipher | None:
    secret = settings.APPLE_TOKEN_ENCRYPTION_KEY.get_secret_value()
    if not secret:
        return None
    return AesGcmSecretCipher(secret, purpose="apple-refresh-token")


@lru_cache
def get_used_provider_tokens() -> UsedProviderTokens:
    return RedisUsedProviderTokens(get_redis)


def get_provider_token_gate(
    google: GoogleTokenVerifier | None = Depends(get_google_verifier),
    apple: AppleSignInGateway | None = Depends(get_apple_gateway),
    used_tokens: UsedProviderTokens = Depends(get_used_provider_tokens),
) -> ProviderTokenGate:
    return ProviderTokenGate(google=google, apple=apple, used_tokens=used_tokens)


def get_external_accounts(
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    pending_repo: PendingSignupRepository = Depends(get_pending_signup_repository),
) -> ExternalAccounts:
    return ExternalAccounts(
        user_repository=user_repo, pending_signup_repository=pending_repo
    )


def get_apple_token_vault(
    cipher: SecretCipher | None = Depends(get_apple_token_cipher),
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
) -> AppleTokenVault | None:
    if cipher is None:
        return None
    return AppleTokenVault(cipher=cipher, user_repository=user_repo)


def get_apple_revoker(
    vault: AppleTokenVault | None = Depends(get_apple_token_vault),
    apple: AppleSignInGateway | None = Depends(get_apple_gateway),
) -> AppleAuthorizationRevoker | None:
    if vault is None or apple is None or not apple.can_exchange_codes:
        return None
    return AppleAuthorizationRevoker(vault=vault, apple=apple)


def get_provider_sign_in_handler(
    gate: ProviderTokenGate = Depends(get_provider_token_gate),
    accounts: ExternalAccounts = Depends(get_external_accounts),
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    auth_event_repo: AuthEventRepository = Depends(get_auth_event_repository),
    session_manager: SessionManager = Depends(get_session_manager),
    revocations: SessionRevocationList = Depends(get_session_revocations),
    email_queue: EmailQueue = Depends(get_email_queue),
    email_config: EmailAuthConfig = Depends(get_email_auth_config),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
    apple_tokens: AppleTokenVault | None = Depends(get_apple_token_vault),
) -> ProviderSignInHandler:
    return ProviderSignInHandler(
        gate=gate,
        accounts=accounts,
        user_repository=user_repo,
        auth_event_repository=auth_event_repo,
        session_manager=session_manager,
        revocations=revocations,
        email_queue=email_queue,
        email_config=email_config,
        uow=uow,
        apple_tokens=apple_tokens,
    )


def get_link_provider_handler(
    gate: ProviderTokenGate = Depends(get_provider_token_gate),
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    auth_event_repo: AuthEventRepository = Depends(get_auth_event_repository),
    email_queue: EmailQueue = Depends(get_email_queue),
    email_config: EmailAuthConfig = Depends(get_email_auth_config),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
    apple_tokens: AppleTokenVault | None = Depends(get_apple_token_vault),
    session_repo: SessionRepository = Depends(get_session_repository),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
) -> LinkProviderHandler:
    return LinkProviderHandler(
        gate=gate,
        session_repository=session_repo,
        password_hasher=password_hasher,
        apple_tokens=apple_tokens,
        user_repository=user_repo,
        auth_event_repository=auth_event_repo,
        email_queue=email_queue,
        email_config=email_config,
        uow=uow,
    )


def get_unlink_provider_handler(
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    auth_event_repo: AuthEventRepository = Depends(get_auth_event_repository),
    email_queue: EmailQueue = Depends(get_email_queue),
    email_config: EmailAuthConfig = Depends(get_email_auth_config),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
    apple_tokens: AppleTokenVault | None = Depends(get_apple_token_vault),
    apple_revoker: AppleAuthorizationRevoker | None = Depends(get_apple_revoker),
) -> UnlinkProviderHandler:
    return UnlinkProviderHandler(
        apple_tokens=apple_tokens,
        apple_revoker=apple_revoker,
        user_repository=user_repo,
        auth_event_repository=auth_event_repo,
        email_queue=email_queue,
        email_config=email_config,
        uow=uow,
    )


def get_apple_notification_handler(
    apple: AppleSignInGateway | None = Depends(get_apple_gateway),
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    session_repo: SessionRepository = Depends(get_session_repository),
    auth_event_repo: AuthEventRepository = Depends(get_auth_event_repository),
    revocations: SessionRevocationList = Depends(get_session_revocations),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> AppleNotificationHandler:
    return AppleNotificationHandler(
        apple=apple,
        user_repository=user_repo,
        session_repository=session_repo,
        auth_event_repository=auth_event_repo,
        revocations=revocations,
        uow=uow,
    )


def get_change_username_handler(
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    pending_repo: PendingSignupRepository = Depends(get_pending_signup_repository),
    auth_event_repo: AuthEventRepository = Depends(get_auth_event_repository),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> ChangeUsernameHandler:
    return ChangeUsernameHandler(
        user_repository=user_repo,
        pending_signup_repository=pending_repo,
        auth_event_repository=auth_event_repo,
        uow=uow,
    )
