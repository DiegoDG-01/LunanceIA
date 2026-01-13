from fastapi import Depends
from sqlalchemy.orm import Session

from application.transactions.commands.update_transaction import (
    UpdateTransactionCommandHandler,
)
from application.transactions.queries.get_transactions import GetTransactionsHandler
from infrastructure.external_services.gemini import GeminiService
from infrastructure.database.connection import get_db
from infrastructure.database.repositories.sqlalchemy_account_repository import (
    SQLAlchemyAccountRepository,
)
from infrastructure.database.repositories.sqlalchemy_transaction_repository import (
    SQLAlchemyTransactionRepository,
)
from domain.services.account_service import AccountService
from application.accounts.commands.create_account import CreateAccountHandler
from application.accounts.commands.update_account import UpdateAccountHandler
from application.accounts.commands.state_account import StateAccountHandler
from application.transactions.commands.create_transaction import (
    CreateTransactionHandler,
)
from application.subscriptions.commands.update_subscription import UpdateSubscriptionHandler
from domain.repositories.account_repository import AccountRepository
from application.transactions.commands.delete_transaction import (
    DeleteTransactionHandler,
)
from domain.repositories.transaction_repository import TransactionRepository

from application.transactions.queries.get_transaction_by_uuid import (
    GetTransactionByUuidHandler,
)
from application.accounts.commands.delete_account import DeleteAccountHandler
from application.accounts.queries.get_user_accounts import GetUserAccountsHandler
from application.accounts.queries.get_account_by_id import GetAccountByIdHandler
from infrastructure.database.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from application.auth.commands.login import LoginHandler
from application.auth.commands.refresh_token import RefreshTokenHandler
from application.auth.commands.logout import LogoutHandler
from application.subscriptions.commands.delete_subscription import DeleteSubscriptionHandler
from application.auth.commands.register import RegisterHandler
from infrastructure.security.jwt_service import JWTService

from domain.repositories.auth_token_repository import AuthTokenRepository
from infrastructure.database.repositories.sqlalchemy_auth_token_repository import (
    SQLAlchemyAuthTokenRepository,
)
from application.categories.queries.get_categories import GetCategoriesHandler
from infrastructure.database.repositories.sqlalchemy_category_repository import (
    SQLAlchemyCategoryRepository,
)

from infrastructure.database.repositories.sqlalchemy_dashboard_repository import SQLAlchemyDashboardRepository
from application.dashboard.queries.get_dashboard_summary import GetDashboardSummaryHandler

from infrastructure.database.repositories.sqlalchemy_subscription_repository import SQLAlchemySubscriptionRepository
from application.subscriptions.commands.create_subscription import CreateSubscriptionHandler
from application.subscriptions.queries.get_subscriptions import GetSubscriptionsHandler


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


def get_gemini_service() -> GeminiService:
    return GeminiService()


def get_category_repository(
        db: Session = Depends(get_db),
) -> SQLAlchemyCategoryRepository:
    return SQLAlchemyCategoryRepository(db)


def get_subscription_repository(
        db: Session = Depends(get_db),
) -> SQLAlchemySubscriptionRepository:
    return SQLAlchemySubscriptionRepository(db)


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


def get_transactions_handler(
        transaction_repo: SQLAlchemyTransactionRepository = Depends(
            get_transaction_repository
        ),
) -> GetTransactionsHandler:
    return GetTransactionsHandler(transaction_repo)


def get_transaction_by_uuid_handler(
        transaction_repository: TransactionRepository = Depends(get_transaction_repository),
) -> GetTransactionByUuidHandler:
    return GetTransactionByUuidHandler(transaction_repository)


def get_account_by_id_handler(
        account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
) -> GetAccountByIdHandler:
    return GetAccountByIdHandler(account_repo)


def get_create_transaction_handler(
        user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
        account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
        transaction_repo: SQLAlchemyTransactionRepository = Depends(
            get_transaction_repository
        ),
        category_repo: SQLAlchemyCategoryRepository = Depends(get_category_repository),
) -> CreateTransactionHandler:
    return CreateTransactionHandler(
        user_repo, account_repo, transaction_repo, category_repo
    )


def get_create_subscription_handler(
        subscription_repo: SQLAlchemySubscriptionRepository = Depends(get_subscription_repository),
        user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
        account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
        category_repo: SQLAlchemyCategoryRepository = Depends(get_category_repository)
) -> CreateSubscriptionHandler:
    return CreateSubscriptionHandler(subscription_repo, user_repo, account_repo, category_repo)

def get_update_subscription_handler(
        subscription_respo: SQLAlchemySubscriptionRepository = Depends(get_subscription_repository),
        category_repo: SQLAlchemyCategoryRepository = Depends(get_category_repository),
        account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
) -> UpdateSubscriptionHandler:
    return UpdateSubscriptionHandler(subscription_respo, category_repo, account_repo)

def get_subscriptions_handler(
        subscription_repo: SQLAlchemySubscriptionRepository = Depends(get_subscription_repository),
        account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
        category_repo: SQLAlchemyCategoryRepository = Depends(get_category_repository),
) -> GetSubscriptionsHandler:
    return GetSubscriptionsHandler(subscription_repo, account_repo, category_repo)

def get_delete_subscription_handler(
        subscription_repo: SQLAlchemySubscriptionRepository = Depends(get_subscription_repository),
) -> DeleteSubscriptionHandler:
    return DeleteSubscriptionHandler(subscription_repo)


def get_delete_transaction_handler(
        transaction_repo: SQLAlchemyTransactionRepository = Depends(
            get_transaction_repository
        ),
        account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
) -> DeleteTransactionHandler:
    return DeleteTransactionHandler(transaction_repo, account_repo)


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


def get_update_transaction_handler(
        transaction_repository: TransactionRepository = Depends(get_transaction_repository),
        account_repository: AccountRepository = Depends(get_account_repository),
) -> UpdateTransactionCommandHandler:
    return UpdateTransactionCommandHandler(transaction_repository, account_repository)


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


def get_categories_handler(db: Session = Depends(get_db)) -> GetCategoriesHandler:
    category_repository = SQLAlchemyCategoryRepository(db)
    return GetCategoriesHandler(category_repository)


def get_dashboard_repository(
        db: Session = Depends(get_db),
) -> SQLAlchemyDashboardRepository:
    return SQLAlchemyDashboardRepository(db)


def get_dashboard_summary_handler(
        dashboard_repository: SQLAlchemyDashboardRepository = Depends(get_dashboard_repository),
) -> GetDashboardSummaryHandler:
    return GetDashboardSummaryHandler(dashboard_repository)
