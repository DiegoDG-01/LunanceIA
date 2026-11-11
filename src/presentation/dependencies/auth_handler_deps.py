from fastapi import Depends

from application.auth.commands.change_password import ChangePasswordHandler
from application.auth.commands.login import LoginHandler
from application.auth.commands.logout import LogoutHandler
from application.auth.commands.password_reset import (
    RequestPasswordResetHandler,
    ResetPasswordHandler,
)
from application.auth.commands.refresh_session import RefreshSessionHandler
from application.auth.commands.register import RegisterHandler
from application.auth.commands.revoke_session import RevokeSessionHandler
from application.auth.commands.verify_email import (
    ResendVerificationHandler,
    VerifyEmailHandler,
)
from application.auth.config import AuthConfig, EmailAuthConfig
from application.auth.queries.list_sessions import ListSessionsHandler
from application.auth.services.login_guard import LoginGuard
from application.auth.services.sessions import SessionManager
from application.interfaces.auth_service import (
    AccessTokenIssuer,
    PasswordHasher,
    SessionRevocationList,
)
from application.interfaces.email import EmailQueue
from domain.repositories.auth.auth_event_repository import AuthEventRepository
from domain.repositories.auth.password_reset_token_repository import (
    PasswordResetTokenRepository,
)
from domain.repositories.auth.pending_signup_repository import PendingSignupRepository
from domain.repositories.auth.refresh_token_repository import RefreshTokenRepository
from domain.repositories.auth.session_repository import SessionRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from infrastructure.database.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from presentation.dependencies.auth_services import (
    get_auth_config,
    get_email_auth_config,
    get_login_guard,
    get_password_hasher,
    get_session_revocations,
    get_token_issuer,
)
from presentation.dependencies.email_deps import get_email_queue
from presentation.dependencies.repositories import (
    get_auth_event_repository,
    get_password_reset_token_repository,
    get_pending_signup_repository,
    get_refresh_token_repository,
    get_session_repository,
    get_unit_of_work_repository,
    get_user_repository,
)


def get_session_manager(
    session_repo: SessionRepository = Depends(get_session_repository),
    refresh_token_repo: RefreshTokenRepository = Depends(get_refresh_token_repository),
    auth_event_repo: AuthEventRepository = Depends(get_auth_event_repository),
    token_issuer: AccessTokenIssuer = Depends(get_token_issuer),
    config: AuthConfig = Depends(get_auth_config),
) -> SessionManager:
    return SessionManager(
        session_repository=session_repo,
        refresh_token_repository=refresh_token_repo,
        auth_event_repository=auth_event_repo,
        token_issuer=token_issuer,
        config=config,
    )


def get_login_handler(
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    auth_event_repo: AuthEventRepository = Depends(get_auth_event_repository),
    session_manager: SessionManager = Depends(get_session_manager),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
    revocations: SessionRevocationList = Depends(get_session_revocations),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
    login_guard: LoginGuard = Depends(get_login_guard),
    session_repo: SessionRepository = Depends(get_session_repository),
    pending_repo: PendingSignupRepository = Depends(get_pending_signup_repository),
) -> LoginHandler:
    return LoginHandler(
        user_repository=user_repo,
        auth_event_repository=auth_event_repo,
        session_manager=session_manager,
        password_hasher=password_hasher,
        revocations=revocations,
        uow=uow,
        login_guard=login_guard,
        session_repository=session_repo,
        pending_signup_repository=pending_repo,
    )


def get_register_handler(
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    pending_repo: PendingSignupRepository = Depends(get_pending_signup_repository),
    auth_event_repo: AuthEventRepository = Depends(get_auth_event_repository),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
    email_queue: EmailQueue = Depends(get_email_queue),
    config: EmailAuthConfig = Depends(get_email_auth_config),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> RegisterHandler:
    return RegisterHandler(
        user_repository=user_repo,
        pending_signup_repository=pending_repo,
        auth_event_repository=auth_event_repo,
        password_hasher=password_hasher,
        email_queue=email_queue,
        config=config,
        uow=uow,
    )


def get_verify_email_handler(
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    pending_repo: PendingSignupRepository = Depends(get_pending_signup_repository),
    auth_event_repo: AuthEventRepository = Depends(get_auth_event_repository),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> VerifyEmailHandler:
    return VerifyEmailHandler(
        user_repository=user_repo,
        pending_signup_repository=pending_repo,
        auth_event_repository=auth_event_repo,
        uow=uow,
    )


def get_resend_verification_handler(
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    pending_repo: PendingSignupRepository = Depends(get_pending_signup_repository),
    auth_event_repo: AuthEventRepository = Depends(get_auth_event_repository),
    email_queue: EmailQueue = Depends(get_email_queue),
    config: EmailAuthConfig = Depends(get_email_auth_config),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> ResendVerificationHandler:
    return ResendVerificationHandler(
        user_repository=user_repo,
        pending_signup_repository=pending_repo,
        auth_event_repository=auth_event_repo,
        email_queue=email_queue,
        config=config,
        uow=uow,
    )


def get_request_password_reset_handler(
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    pending_repo: PendingSignupRepository = Depends(get_pending_signup_repository),
    reset_repo: PasswordResetTokenRepository = Depends(
        get_password_reset_token_repository
    ),
    auth_event_repo: AuthEventRepository = Depends(get_auth_event_repository),
    email_queue: EmailQueue = Depends(get_email_queue),
    config: EmailAuthConfig = Depends(get_email_auth_config),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> RequestPasswordResetHandler:
    return RequestPasswordResetHandler(
        user_repository=user_repo,
        pending_signup_repository=pending_repo,
        reset_token_repository=reset_repo,
        auth_event_repository=auth_event_repo,
        email_queue=email_queue,
        config=config,
        uow=uow,
    )


def get_reset_password_handler(
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    reset_repo: PasswordResetTokenRepository = Depends(
        get_password_reset_token_repository
    ),
    session_repo: SessionRepository = Depends(get_session_repository),
    auth_event_repo: AuthEventRepository = Depends(get_auth_event_repository),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
    revocations: SessionRevocationList = Depends(get_session_revocations),
    login_guard: LoginGuard = Depends(get_login_guard),
    email_queue: EmailQueue = Depends(get_email_queue),
    config: EmailAuthConfig = Depends(get_email_auth_config),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> ResetPasswordHandler:
    return ResetPasswordHandler(
        user_repository=user_repo,
        reset_token_repository=reset_repo,
        session_repository=session_repo,
        auth_event_repository=auth_event_repo,
        password_hasher=password_hasher,
        revocations=revocations,
        login_guard=login_guard,
        email_queue=email_queue,
        config=config,
        uow=uow,
    )


def get_change_password_handler(
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    reset_repo: PasswordResetTokenRepository = Depends(
        get_password_reset_token_repository
    ),
    session_repo: SessionRepository = Depends(get_session_repository),
    auth_event_repo: AuthEventRepository = Depends(get_auth_event_repository),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
    revocations: SessionRevocationList = Depends(get_session_revocations),
    email_queue: EmailQueue = Depends(get_email_queue),
    config: EmailAuthConfig = Depends(get_email_auth_config),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> ChangePasswordHandler:
    return ChangePasswordHandler(
        user_repository=user_repo,
        reset_token_repository=reset_repo,
        session_repository=session_repo,
        auth_event_repository=auth_event_repo,
        password_hasher=password_hasher,
        revocations=revocations,
        email_queue=email_queue,
        config=config,
        uow=uow,
    )


def get_refresh_session_handler(
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    session_repo: SessionRepository = Depends(get_session_repository),
    refresh_token_repo: RefreshTokenRepository = Depends(get_refresh_token_repository),
    auth_event_repo: AuthEventRepository = Depends(get_auth_event_repository),
    session_manager: SessionManager = Depends(get_session_manager),
    revocations: SessionRevocationList = Depends(get_session_revocations),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
    config: AuthConfig = Depends(get_auth_config),
) -> RefreshSessionHandler:
    return RefreshSessionHandler(
        user_repository=user_repo,
        session_repository=session_repo,
        refresh_token_repository=refresh_token_repo,
        auth_event_repository=auth_event_repo,
        session_manager=session_manager,
        revocations=revocations,
        uow=uow,
        config=config,
    )


def get_logout_handler(
    session_repo: SessionRepository = Depends(get_session_repository),
    refresh_token_repo: RefreshTokenRepository = Depends(get_refresh_token_repository),
    auth_event_repo: AuthEventRepository = Depends(get_auth_event_repository),
    revocations: SessionRevocationList = Depends(get_session_revocations),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> LogoutHandler:
    return LogoutHandler(
        session_repository=session_repo,
        refresh_token_repository=refresh_token_repo,
        auth_event_repository=auth_event_repo,
        revocations=revocations,
        uow=uow,
    )


def get_list_sessions_handler(
    session_repo: SessionRepository = Depends(get_session_repository),
) -> ListSessionsHandler:
    return ListSessionsHandler(session_repository=session_repo)


def get_revoke_session_handler(
    session_repo: SessionRepository = Depends(get_session_repository),
    auth_event_repo: AuthEventRepository = Depends(get_auth_event_repository),
    revocations: SessionRevocationList = Depends(get_session_revocations),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> RevokeSessionHandler:
    return RevokeSessionHandler(
        session_repository=session_repo,
        auth_event_repository=auth_event_repo,
        revocations=revocations,
        uow=uow,
    )
