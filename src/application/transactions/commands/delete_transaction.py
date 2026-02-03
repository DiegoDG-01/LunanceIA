from dataclasses import dataclass

from domain.repositories.transaction_repository import TransactionRepository
from domain.repositories.account_repository import AccountRepository

from shared.exceptions.domain import TransactionNotFoundError


@dataclass
class DeleteTransactionCommand:
    uuid: str
    user_id: int


class DeleteTransactionHandler:
    def __init__(
        self,
        transaction_repository: TransactionRepository,
        account_repository: AccountRepository,
    ):
        self.transaction_repository = transaction_repository
        self.account_repository = account_repository

    async def handle(self, command: DeleteTransactionCommand):
        transaction = await self.transaction_repository.get_by_uuid_and_user_id(
            command.uuid, command.user_id
        )

        if not transaction:
            raise TransactionNotFoundError(command.uuid)

        account = await self.account_repository.get_by_id(transaction.account_id)

        if transaction.is_expense():
            new_balance = account.current_balance.add(transaction.amount)
        elif transaction.is_income():
            new_balance = account.current_balance.subtract(transaction.amount)
        else:
            raise ValueError("Transaction type not supported")

        account.update_balance(new_balance)

        await self.account_repository.update(account)

        deleted = await self.transaction_repository.delete_by_uuid(
            command.uuid, command.user_id
        )

        if not deleted:
            raise ValueError(f"Transaction {command.uuid} not found or access denied")

        return True
