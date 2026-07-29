from dataclasses import dataclass
from datetime import date
from typing import cast

from domain.objects.enums import TransactionType
from domain.objects.money import Money
from domain.entities.transaction import Transaction
from domain.repositories.account_repository import AccountRepository
from domain.repositories.installment_charge_repository import (
    InstallmentChargeRepository,
)
from domain.repositories.installment_purchase_repository import (
    InstallmentPurchaseRepository,
)
from domain.repositories.transaction_repository import TransactionRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from application.dto.installment_dto import InstallmentChargeResponseDTO
from shared.exceptions.domain import (
    AccountNotFoundError,
    InstallmentChargeAlreadyPaidError,
    InstallmentChargeNotFoundError,
)


@dataclass
class PayInstallmentChargeCommand:
    user_id: int
    charge_uuid: str
    payment_date: date


class PayInstallmentChargeHandler:
    def __init__(
        self,
        account_repository: AccountRepository,
        transaction_repository: TransactionRepository,
        installment_charge_repository: InstallmentChargeRepository,
        installment_purchase_repository: InstallmentPurchaseRepository,
        uow: AbstractUnitOfWork,
    ):
        self.account_repository = account_repository
        self.transaction_repository = transaction_repository
        self.installment_charge_repository = installment_charge_repository
        self.installment_purchase_repository = installment_purchase_repository
        self.uow = uow

    async def handle(
        self, command: PayInstallmentChargeCommand
    ) -> InstallmentChargeResponseDTO:
        charge_preview = await self.installment_charge_repository.get_by_uuid(
            command.charge_uuid
        )
        if not charge_preview:
            raise InstallmentChargeNotFoundError(command.charge_uuid)

        async with self.uow:
            purchase = await self.installment_purchase_repository.get_by_id(
                purchase_id=charge_preview.installment_purchase_id, for_update=True
            )
            if not purchase or purchase.user_id != command.user_id:
                raise InstallmentChargeNotFoundError(command.charge_uuid)

            account = await self.account_repository.get_by_id(
                cast(int, purchase.account_id), for_update=True
            )
            if not account or account.user_id != command.user_id:
                raise AccountNotFoundError(account_uuid=str(purchase.account_id))

            charge = await self.installment_charge_repository.get_by_uuid(
                command.charge_uuid, for_update=True
            )
            if not charge:
                raise InstallmentChargeNotFoundError(command.charge_uuid)

            if charge.paid:
                raise InstallmentChargeAlreadyPaidError(command.charge_uuid)

            money = Money(charge.amount)
            new_balance = account.current_balance.add(money)

            transaction = Transaction.create_new(
                user_id=command.user_id,
                account_id=cast(int, account.id),
                category_id=purchase.category_id,
                transaction_type=TransactionType.INCOME,
                amount=money,
                transaction_date=command.payment_date,
                description=f"Payment for installment {purchase.description} ({charge.installment_number}/{purchase.num_installments})",
                notes=f"Payment for installment {purchase.id}",
            )

            account.update_balance(new_balance)
            await self.account_repository.update(account)

            transaction = await self.transaction_repository.create(transaction)
            charge.mark_as_paid(cast(int, transaction.id))
            charge = await self.installment_charge_repository.update(charge)

            all_charges = await self.installment_charge_repository.get_by_purchase_id(
                purchase_id=purchase.id
            )
            if all(c.paid for c in all_charges):
                purchase.is_active = False
                await self.installment_purchase_repository.update(purchase)

            await self.uow.commit()

        return InstallmentChargeResponseDTO(
            uuid=cast(str, charge.uuid),
            installment_number=charge.installment_number,
            amount=charge.amount,
            due_date=charge.due_date,
            paid=charge.paid,
            paid_at=charge.paid_at,
        )
