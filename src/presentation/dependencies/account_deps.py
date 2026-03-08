from fastapi import Depends

from application.accounts.commands.create_account import CreateAccountHandler
from application.accounts.commands.update_account import UpdateAccountHandler
from application.accounts.commands.delete_account import DeleteAccountHandler
from application.accounts.commands.state_account import StateAccountHandler
from application.accounts.queries.get_user_accounts import GetUserAccountsHandler
from application.accounts.queries.get_account_by_id import GetAccountByIdHandler
from application.accounts.queries.get_account_activity import (
    GetAccountActivitiesHandler,
)
from domain.services.account_service import AccountService
from infrastructure.database.repositories.sqlalchemy_account_repository import (
    SQLAlchemyAccountRepository,
)
from infrastructure.database.repositories.sqlalchemy_bank_repository import (
    SQLAlchemyBankRepository,
)
from infrastructure.database.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from infrastructure.database.repositories.sqlalchemy_transaction_repository import (
    SQLAlchemyTransactionRepository,
)
from infrastructure.database.repositories.sqlalchemy_credit_card_repository import (
    SQLAlchemyCreditCardSettingsRepository,
)
from infrastructure.database.repositories.sqlalchemy_investment_card_repository import (
    SQLAlchemyInvestmentSettingsRepository,
)

from domain.repositories.unit_of_work import AbstractUnitOfWork
from presentation.dependencies.repositories import (
    get_account_repository,
    get_user_repository,
    get_transaction_repository,
    get_credit_card_settings_repository,
    get_investment_settings_repository,
    get_bank_repository,
    get_unit_of_work_repository,
)
from presentation.dependencies.services import get_account_service


def get_create_account_handler(
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    cc_settings_repo: SQLAlchemyCreditCardSettingsRepository = Depends(
        get_credit_card_settings_repository
    ),
    investment_settings_repo: SQLAlchemyInvestmentSettingsRepository = Depends(
        get_investment_settings_repository
    ),
    bank_repo: SQLAlchemyBankRepository = Depends(get_bank_repository),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> CreateAccountHandler:
    return CreateAccountHandler(
        account_repo,
        user_repo,
        cc_settings_repo,
        investment_settings_repo,
        bank_repo,
        uow,
    )


def get_update_account_handler(
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    bank_repo: SQLAlchemyBankRepository = Depends(get_bank_repository),
    credit_card_repo: SQLAlchemyCreditCardSettingsRepository = Depends(
        get_credit_card_settings_repository
    ),
    investment_card_repo: SQLAlchemyInvestmentSettingsRepository = Depends(
        get_investment_settings_repository
    ),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> UpdateAccountHandler:
    return UpdateAccountHandler(
        account_repo, bank_repo, credit_card_repo, investment_card_repo, uow
    )


def get_delete_account_handler(
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    transaction_repo: SQLAlchemyTransactionRepository = Depends(
        get_transaction_repository
    ),
    account_service: AccountService = Depends(get_account_service),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> DeleteAccountHandler:
    return DeleteAccountHandler(account_repo, transaction_repo, account_service, uow)


def get_state_account_handler(
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    account_service: AccountService = Depends(get_account_service),
    bank_repository: SQLAlchemyBankRepository = Depends(get_bank_repository),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> StateAccountHandler:
    return StateAccountHandler(account_repo, account_service, bank_repository, uow)


def get_user_accounts_handler(
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    bank_repo: SQLAlchemyBankRepository = Depends(get_bank_repository),
    credit_card_repository: SQLAlchemyCreditCardSettingsRepository = Depends(
        get_credit_card_settings_repository
    ),
    investment_card_repository: SQLAlchemyInvestmentSettingsRepository = Depends(
        get_investment_settings_repository
    ),
) -> GetUserAccountsHandler:
    return GetUserAccountsHandler(
        account_repo,
        bank_repo,
        credit_card_repository,
        investment_card_repository,
    )


def get_account_by_id_handler(
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    bank_repo: SQLAlchemyBankRepository = Depends(get_bank_repository),
) -> GetAccountByIdHandler:
    return GetAccountByIdHandler(account_repo, bank_repo)


def get_activity_account_handler(
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    bank_repo: SQLAlchemyBankRepository = Depends(get_bank_repository),
    transaction_repo: SQLAlchemyTransactionRepository = Depends(
        get_transaction_repository
    ),
) -> GetAccountActivitiesHandler:
    return GetAccountActivitiesHandler(account_repo, bank_repo, transaction_repo)
