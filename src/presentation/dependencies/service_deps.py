from fastapi import Depends
from sqlalchemy.orm import Session

from infrastructure.database.connection import get_db
from infrastructure.database.repositories.sqlalchemy_account_repository import (
    SQLAlchemyAccountRepository,
)
from infrastructure.database.repositories.sqlalchemy_transaction_repository import (
    SQLAlchemyTransactionRepository,
)
from domain.services.account_service import AccountService
from application.commands.create_account_command import CreateAccountHandler
from application.commands.update_account_command import UpdateAccountHandler
from application.commands.state_account_command import StateAccountHandler
from application.commands.delete_account_command import DeleteAccountHandler
from application.queries.get_user_accounts_query import GetUserAccountsHandler
from application.queries.get_account_by_id_query import GetAccountByIdHandler
from infrastructure.database.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from application.commands.auth_commands import (
    LoginHandler,
    RefreshTokenHandler,
    LogoutHandler,
)
from application.commands.register_commands import RegisterHandler
from infrastructure.security.jwt_service import JWTService

from domain.repositories.auth_token_repository import AuthTokenRepository
from infrastructure.database.repositories.sqlalchemy_auth_token_repository import (
    SQLAlchemyAuthTokenRepository,
)


# Repository Dependencies
def get_account_repository(
    db: Session = Depends(get_db),
) -> SQLAlchemyAccountRepository:
    return SQLAlchemyAccountRepository(db)


def get_user_repository(db: Session = Depends(get_db)) -> SQLAlchemyUserRepository:
    return SQLAlchemyUserRepository(db)


def get_transaction_repository(
    db: Session = Depends(get_db),
) -> SQLAlchemyTransactionRepository:
    return SQLAlchemyTransactionRepository(db)


# Service Dependencies
def get_account_service() -> AccountService:
    return AccountService()


# Command Handler Dependencies
def get_create_account_handler(
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
) -> CreateAccountHandler:
    return CreateAccountHandler(account_repo, user_repo)


def get_update_account_handler(
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
) -> UpdateAccountHandler:
    return UpdateAccountHandler(account_repo)


def get_delete_account_handler(
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    transaction_repo: SQLAlchemyTransactionRepository = Depends(
        get_transaction_repository
    ),
    account_service: AccountService = Depends(get_account_service),
) -> DeleteAccountHandler:
    return DeleteAccountHandler(account_repo, transaction_repo, account_service)


def get_state_account_handler(
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    account_service: AccountService = Depends(get_account_service),
) -> StateAccountHandler:
    return StateAccountHandler(account_repo, account_service)


# Query Handler Dependencies
def get_user_accounts_handler(
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
) -> GetUserAccountsHandler:
    return GetUserAccountsHandler(account_repo)


def get_account_by_id_handler(
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
) -> GetAccountByIdHandler:
    return GetAccountByIdHandler(account_repo)


def get_auth_token_repository(db: Session = Depends(get_db)) -> AuthTokenRepository:
    return SQLAlchemyAuthTokenRepository(db)


def get_jwt_service(
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    auth_token_repo: AuthTokenRepository = Depends(get_auth_token_repository),
) -> JWTService:
    return JWTService(user_repo, auth_token_repo)


def get_login_handler(
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    auth_token_repo: AuthTokenRepository = Depends(get_auth_token_repository),
    jwt_service: JWTService = Depends(get_jwt_service),
) -> LoginHandler:
    return LoginHandler(user_repo, auth_token_repo, jwt_service)


def get_register_handler(
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    jwt_service: JWTService = Depends(get_jwt_service),
) -> RegisterHandler:
    return RegisterHandler(user_repo, jwt_service)


def get_refresh_token_handler(
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    auth_token_repository: AuthTokenRepository = Depends(get_auth_token_repository),
    jwt_service: JWTService = Depends(get_jwt_service),
) -> RefreshTokenHandler:
    return RefreshTokenHandler(user_repo, auth_token_repository, jwt_service)


def get_logout_handler(
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    auth_token_repository: AuthTokenRepository = Depends(get_auth_token_repository),
    jwt_service: JWTService = Depends(get_jwt_service),
) -> LogoutHandler:
    return LogoutHandler(user_repo, auth_token_repository, jwt_service)
