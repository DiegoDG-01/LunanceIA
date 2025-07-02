from fastapi import Depends
from sqlalchemy.orm import Session

from infrastructure.database.connection import get_db
from infrastructure.database.repositories.sqlalchemy_account_repository import SQLAlchemyAccountRepository
# from infrastructure.database.repositories.sqlalchemy_user_repository import SQLAlchemyUserRepository
from infrastructure.database.repositories.sqlalchemy_transaction_repository import SQLAlchemyTransactionRepository
from domain.services.account_service import AccountService
from application.commands.create_account_command import CreateAccountHandler
from application.commands.update_account_command import UpdateAccountHandler
from application.commands.delete_account_command import DeleteAccountHandler
from application.queries.get_user_accounts_query import GetUserAccountsHandler
from application.queries.get_account_by_id_query import GetAccountByIdHandler
from infrastructure.database.repositories.sqlalchemy_user_repository import SQLAlchemyUserRepository
from application.commands.auth_commands import LoginHandler, RefreshTokenHandler
from application.commands.register_commands import RegisterHandler


# Repository Dependencies
def get_account_repository(db: Session = Depends(get_db)) -> SQLAlchemyAccountRepository:
    return SQLAlchemyAccountRepository(db)


def get_user_repository(db: Session = Depends(get_db)) -> SQLAlchemyUserRepository:
    return SQLAlchemyUserRepository(db)


def get_transaction_repository(db: Session = Depends(get_db)) -> SQLAlchemyTransactionRepository:
    return SQLAlchemyTransactionRepository(db)


# Service Dependencies
def get_account_service() -> AccountService:
    return AccountService()


# Command Handler Dependencies
def get_create_account_handler(
        account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
        user_repo: SQLAlchemyUserRepository = Depends(get_user_repository)
) -> CreateAccountHandler:
    return CreateAccountHandler(account_repo, user_repo)


def get_update_account_handler(
        account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository)
) -> UpdateAccountHandler:
    return UpdateAccountHandler(account_repo)


def get_delete_account_handler(
        account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
        transaction_repo: SQLAlchemyTransactionRepository = Depends(get_transaction_repository),
        account_service: AccountService = Depends(get_account_service)
) -> DeleteAccountHandler:
    return DeleteAccountHandler(account_repo, transaction_repo, account_service)


# Query Handler Dependencies
def get_user_accounts_handler(
        account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository)
) -> GetUserAccountsHandler:
    return GetUserAccountsHandler(account_repo)


def get_account_by_id_handler(
        account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository)
) -> GetAccountByIdHandler:
    return GetAccountByIdHandler(account_repo)


def get_login_handler(
        user_repo: SQLAlchemyUserRepository = Depends(get_user_repository)
) -> LoginHandler:
    return LoginHandler(user_repo)


def get_register_handler(
        user_repo: SQLAlchemyUserRepository = Depends(get_user_repository)
) -> RegisterHandler:
    return RegisterHandler(user_repo)


def get_refresh_token_handler(
        user_repo: SQLAlchemyUserRepository = Depends(get_user_repository)
) -> RefreshTokenHandler:
    return RefreshTokenHandler(user_repo)
