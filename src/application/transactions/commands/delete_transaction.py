from dataclasses import dataclass
from typing import cast

from domain.repositories.accounts.account_repository import AccountRepository
from domain.repositories.installments.installment_purchase_repository import (
    InstallmentPurchaseRepository,
)
from domain.repositories.securities.trade_repository import SecurityTradeRepository
from domain.repositories.transactions.transaction_repository import (
    TransactionRepository,
)
from domain.repositories.unit_of_work import AbstractUnitOfWork
from shared.exceptions.domain import (
    AccountNotFoundError,
    InstallmentTransactionModificationError,
    InvalidTransactionTypeError,
    SecurityTradeTransactionLockedError,
    TransactionNotFoundError,
)


@dataclass
class DeleteTransactionCommand:
    uuid: str
    user_id: int


class DeleteTransactionHandler:
    def __init__(
        self,
        transaction_repository: TransactionRepository,
        account_repository: AccountRepository,
        installment_purchase_repository: InstallmentPurchaseRepository,
        uow: AbstractUnitOfWork,
        security_trade_repository: SecurityTradeRepository | None = None,
    ):
        self.transaction_repository = transaction_repository
        self.account_repository = account_repository
        self.installment_purchase_repository = installment_purchase_repository
        self.uow = uow
        # El dinero de una operación de acciones se mueve desde /securities/trades.
        self.security_trade_repository = security_trade_repository

    async def handle(self, command: DeleteTransactionCommand):
        async with self.uow:
            transaction = await self.transaction_repository.get_by_uuid_and_user_id(
                command.uuid, command.user_id, for_update=True
            )

            if not transaction:
                raise TransactionNotFoundError(command.uuid)

            purchase = await self.installment_purchase_repository.get_by_initial_transaction_id(
                transaction.id, command.user_id
            )
            if purchase:
                raise InstallmentTransactionModificationError()

            if (
                self.security_trade_repository is not None
                and await self.security_trade_repository.exists_for_transaction(
                    cast(int, transaction.id)
                )
            ):
                raise SecurityTradeTransactionLockedError()

            account = await self.account_repository.get_by_id(
                transaction.account_id, for_update=True
            )

            if not account:
                raise AccountNotFoundError(str(transaction.account_id))

            if transaction.is_expense():
                new_balance = account.current_balance.add(transaction.amount)
            elif transaction.is_income():
                new_balance = account.current_balance.subtract(transaction.amount)
            else:
                raise InvalidTransactionTypeError(transaction.transaction_type.value)

            account.update_balance(new_balance)

            await self.account_repository.update(account)

            deleted = await self.transaction_repository.delete_by_uuid(
                command.uuid, command.user_id
            )

            if not deleted:
                raise TransactionNotFoundError(command.uuid)

            await self.uow.commit()

        return True
