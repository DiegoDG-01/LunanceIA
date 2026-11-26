from dataclasses import dataclass
from typing import cast

from domain.objects.enums import TransactionType
from domain.repositories.accounts.account_repository import AccountRepository
from domain.repositories.installments.installment_charge_repository import (
    InstallmentChargeRepository,
)
from domain.repositories.installments.installment_purchase_repository import (
    InstallmentPurchaseRepository,
)
from domain.repositories.transactions.transaction_repository import (
    TransactionRepository,
)
from domain.repositories.unit_of_work import AbstractUnitOfWork
from shared.exceptions.domain import (
    AccountNotFoundError,
    BulkDeleteFailedError,
    InstallmentPurchaseNotFoundError,
)


@dataclass
class DeleteInstallmentPurchaseCommand:
    user_id: int
    purchase_uuid: str


class DeleteInstallmentPurchaseHandler:
    def __init__(
        self,
        account_repository: AccountRepository,
        transaction_repository: TransactionRepository,
        installment_purchase_repository: InstallmentPurchaseRepository,
        installment_charge_repository: InstallmentChargeRepository,
        uow: AbstractUnitOfWork,
    ):
        self.account_repository = account_repository
        self.transaction_repository = transaction_repository
        self.installment_purchase_repository = installment_purchase_repository
        self.installment_charge_repository = installment_charge_repository
        self.uow = uow

    async def handle(self, command: DeleteInstallmentPurchaseCommand):
        async with self.uow:
            purchase = await self.installment_purchase_repository.get_by_uuid(
                uuid=command.purchase_uuid, user_id=command.user_id, for_update=True
            )
            if not purchase:
                raise InstallmentPurchaseNotFoundError(
                    purchase_uuid=command.purchase_uuid
                )

            charges = await self.installment_charge_repository.get_by_purchase_id(
                purchase_id=cast(int, purchase.id), for_update=True
            )

            # Toda compra se registra con su gasto inicial; sin él no hay forma
            # confiable de saber qué se movió, así que no se borra a ciegas.
            if purchase.initial_transaction_id is None:
                raise BulkDeleteFailedError(entity="initial installment transaction")

            await self._delete_purchase_with_linked_transactions(
                command=command, purchase=purchase, charges=charges
            )

            await self.installment_charge_repository.delete_by_purchase_id(
                purchase_id=cast(int, purchase.id)
            )
            await self.installment_purchase_repository.delete(
                purchase_uuid=cast(str, purchase.uuid)
            )
            await self.uow.commit()

    async def _delete_purchase_with_linked_transactions(
        self, command, purchase, charges
    ) -> None:
        """Revierte el gasto inicial y todas las transferencias de sus cuotas."""
        initial_transaction = await self.transaction_repository.get_by_id(
            cast(int, purchase.initial_transaction_id), for_update=True
        )
        if not initial_transaction or initial_transaction.user_id != command.user_id:
            raise BulkDeleteFailedError(entity="initial installment transaction")

        transactions = [initial_transaction]
        transfer_uuids = set()
        for charge in charges:
            if not charge.paid or charge.transaction_id is None:
                continue
            incoming = await self.transaction_repository.get_by_id(
                charge.transaction_id, for_update=True
            )
            if (
                not incoming
                or incoming.user_id != command.user_id
                or incoming.transaction_type != TransactionType.TRANSFER
                or not incoming.transfer_uuid
            ):
                raise BulkDeleteFailedError(entity="installment payment transaction")
            transfer_uuids.add(incoming.transfer_uuid)

        for transfer_uuid in transfer_uuids:
            transfer_transactions = (
                await self.transaction_repository.get_by_transfer_uuid(
                    transfer_uuid, command.user_id, for_update=True
                )
            )
            if len(transfer_transactions) != 2:
                raise BulkDeleteFailedError(entity="installment payment transfer")
            transactions.extend(transfer_transactions)

        locked_accounts = {}
        for account_id in sorted(
            {transaction.account_id for transaction in transactions}
        ):
            account = await self.account_repository.get_by_id(
                account_id, for_update=True
            )
            if not account or account.user_id != command.user_id:
                raise AccountNotFoundError(account_uuid=str(account_id))
            locked_accounts[account_id] = account

        # El gasto original se revierte en la TDC. Cada transferencia se revierte
        # devolviendo fondos al origen y reduciendo el disponible recuperado en la TDC.
        initial_account = locked_accounts[initial_transaction.account_id]
        initial_account.update_balance(
            initial_account.current_balance.add(initial_transaction.amount)
        )
        for transaction in transactions[1:]:
            account = locked_accounts[transaction.account_id]
            if transaction.account_id == purchase.account_id:
                account.update_balance(
                    account.current_balance.subtract(transaction.amount)
                )
            else:
                account.update_balance(account.current_balance.add(transaction.amount))

        for account in locked_accounts.values():
            await self.account_repository.update(account)

        transaction_ids = [cast(int, transaction.id) for transaction in transactions]
        deleted = await self.transaction_repository.delete_bulk_by_ids(
            transaction_ids=transaction_ids, user_id=command.user_id
        )
        if not deleted:
            raise BulkDeleteFailedError(entity="transactions")
