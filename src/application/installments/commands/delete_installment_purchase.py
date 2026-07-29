from typing import cast
from dataclasses import dataclass
from decimal import Decimal

from domain.objects.money import Money
from domain.repositories.account_repository import AccountRepository
from domain.repositories.installment_charge_repository import (
    InstallmentChargeRepository,
)
from domain.repositories.installment_purchase_repository import (
    InstallmentPurchaseRepository,
)
from domain.repositories.transaction_repository import TransactionRepository
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

            account = await self.account_repository.get_by_id(
                purchase.account_id, for_update=True
            )
            if not account:
                raise AccountNotFoundError(account_uuid=str(purchase.account_id))

            charges = await self.installment_charge_repository.get_by_purchase_id(
                purchase_id=cast(int, purchase.id), for_update=True
            )

            paid_total = Decimal("0")
            transactions_ids_to_delete = []
            for charge in charges:
                if charge.paid and charge.transaction_id is not None:
                    paid_total += charge.amount
                    transactions_ids_to_delete.append(charge.transaction_id)

            net_restore = purchase.total_amount.amount - paid_total
            new_balance = account.current_balance.add(Money(net_restore))
            account.update_balance(new_balance)

            if transactions_ids_to_delete:
                deleted = await self.transaction_repository.delete_bulk_by_ids(
                    transaction_ids=transactions_ids_to_delete, user_id=command.user_id
                )
                if not deleted:
                    raise BulkDeleteFailedError(entity="transactions")

            await self.installment_charge_repository.delete_by_purchase_id(
                purchase_id=cast(int, purchase.id)
            )
            await self.installment_purchase_repository.delete(
                purchase_uuid=cast(str, purchase.uuid)
            )
            await self.account_repository.update(account)
            await self.uow.commit()
