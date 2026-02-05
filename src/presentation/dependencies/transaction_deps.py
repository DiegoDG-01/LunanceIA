from fastapi import Depends

from application.transactions.commands.create_transaction import (
    CreateTransactionHandler,
)
from application.transactions.commands.update_transaction import (
    UpdateTransactionCommandHandler,
)
from application.transactions.commands.delete_transaction import (
    DeleteTransactionHandler,
)
from application.transactions.queries.get_transactions import GetTransactionsHandler
from application.transactions.queries.get_transaction_by_uuid import (
    GetTransactionByUuidHandler,
)
from domain.repositories.account_repository import AccountRepository
from domain.repositories.transaction_repository import TransactionRepository
from infrastructure.database.repositories.sqlalchemy_account_repository import (
    SQLAlchemyAccountRepository,
)
from infrastructure.database.repositories.sqlalchemy_transaction_repository import (
    SQLAlchemyTransactionRepository,
)
from infrastructure.database.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from infrastructure.database.repositories.sqlalchemy_category_repository import (
    SQLAlchemyCategoryRepository,
)
from infrastructure.database.repositories.sqlalchemy_bank_repository import (
    SQLAlchemyBankRepository,
)

from presentation.dependencies.repositories import (
    get_account_repository,
    get_user_repository,
    get_transaction_repository,
    get_category_repository,
    get_bank_repository,
)


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


def get_create_transaction_handler(
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    transaction_repo: SQLAlchemyTransactionRepository = Depends(
        get_transaction_repository
    ),
    category_repo: SQLAlchemyCategoryRepository = Depends(get_category_repository),
    bank_repo: SQLAlchemyBankRepository = Depends(get_bank_repository),
) -> CreateTransactionHandler:
    return CreateTransactionHandler(
        user_repo, account_repo, transaction_repo, category_repo, bank_repo
    )


def get_update_transaction_handler(
    transaction_repository: TransactionRepository = Depends(get_transaction_repository),
    account_repository: AccountRepository = Depends(get_account_repository),
) -> UpdateTransactionCommandHandler:
    return UpdateTransactionCommandHandler(transaction_repository, account_repository)


def get_delete_transaction_handler(
    transaction_repo: SQLAlchemyTransactionRepository = Depends(
        get_transaction_repository
    ),
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
) -> DeleteTransactionHandler:
    return DeleteTransactionHandler(transaction_repo, account_repo)
