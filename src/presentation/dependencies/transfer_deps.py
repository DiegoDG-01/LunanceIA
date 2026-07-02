from fastapi import Depends

from application.transfers.commands.create_transfer import CreateTransferHandler
from application.transfers.commands.delete_transfer import DeleteTransferHandler
from domain.repositories.account_repository import AccountRepository
from domain.repositories.transaction_repository import TransactionRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from domain.repositories.user_repository import UserRepository
from presentation.dependencies.repositories import (
    get_account_repository,
    get_transaction_repository,
    get_unit_of_work_repository,
    get_user_repository,
)


def get_create_transfer_handler(
    user_repo: UserRepository = Depends(get_user_repository),
    account_repo: AccountRepository = Depends(get_account_repository),
    transaction_repo: TransactionRepository = Depends(get_transaction_repository),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> CreateTransferHandler:
    return CreateTransferHandler(user_repo, account_repo, transaction_repo, uow)

def get_delete_transfer_handler(
    transaction_repo: TransactionRepository = Depends(get_transaction_repository),
    account_repo: AccountRepository = Depends(get_account_repository),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> DeleteTransferHandler:
    return DeleteTransferHandler(transaction_repo, account_repo, uow)
