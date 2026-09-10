import uuid as uuid_lib
from dataclasses import dataclass
from datetime import date
from typing import cast

from application.dto.installment_dto import InstallmentChargeResponseDTO
from domain.entities.transaction import Transaction
from domain.objects.enums import AccountType, TransactionType
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
    InstallmentChargeAlreadyPaidError,
    InstallmentChargeNotFoundError,
    InsufficientFundsError,
    SameAccountTransferError,
    TransferAccountTypeNotAllowedError,
)


@dataclass
class PayInstallmentChargeCommand:
    user_id: int
    charge_uuid: str
    source_account_uuid: str
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

            source_preview = await self.account_repository.get_by_uuid_and_user_id(
                command.source_account_uuid, command.user_id
            )
            if not source_preview:
                raise AccountNotFoundError(account_uuid=command.source_account_uuid)

            if source_preview.id == purchase.account_id:
                raise SameAccountTransferError()

            locked_accounts = {}
            for account_id in sorted(
                {cast(int, purchase.account_id), cast(int, source_preview.id)}
            ):
                locked_account = await self.account_repository.get_by_id(
                    account_id, for_update=True
                )
                if not locked_account or locked_account.user_id != command.user_id:
                    raise AccountNotFoundError(account_uuid=str(account_id))
                locked_accounts[account_id] = locked_account

            account = locked_accounts[cast(int, purchase.account_id)]
            source_account = locked_accounts[cast(int, source_preview.id)]

            if source_account.account_type == AccountType.CREDIT_CARD:
                raise TransferAccountTypeNotAllowedError(
                    source_account.account_type.value
                )

            charge = await self.installment_charge_repository.get_by_uuid(
                command.charge_uuid, for_update=True
            )
            if not charge:
                raise InstallmentChargeNotFoundError(command.charge_uuid)

            if charge.paid:
                raise InstallmentChargeAlreadyPaidError(command.charge_uuid)

            money = Money(charge.amount)
            if not source_account.can_withdraw(money):
                raise InsufficientFundsError(
                    required_amount=float(money.amount),
                    available_amount=float(source_account.current_balance.amount),
                )

            transfer_uuid = str(uuid_lib.uuid4())
            description = (
                f"Pago de cuota {purchase.description} "
                f"({charge.installment_number}/{purchase.num_installments})"
            )
            outgoing = Transaction.create_new(
                user_id=command.user_id,
                account_id=cast(int, source_account.id),
                category_id=None,
                transaction_type=TransactionType.TRANSFER,
                amount=money,
                transaction_date=command.payment_date,
                description=f"{description} a {account.name}",
                notes=f"Pago de compra a meses {purchase.id}",
            )
            outgoing.transfer_uuid = transfer_uuid

            incoming = Transaction.create_new(
                user_id=command.user_id,
                account_id=cast(int, account.id),
                category_id=None,
                transaction_type=TransactionType.TRANSFER,
                amount=money,
                transaction_date=command.payment_date,
                description=f"{description} desde {source_account.name}",
                notes=f"Pago de compra a meses {purchase.id}",
            )
            incoming.transfer_uuid = transfer_uuid

            source_account.update_balance(
                source_account.current_balance.subtract(money)
            )
            account.update_balance(account.current_balance.add(money))
            await self.account_repository.update(source_account)
            await self.account_repository.update(account)

            await self.transaction_repository.create(outgoing)
            incoming = await self.transaction_repository.create(incoming)
            charge.mark_as_paid(cast(int, incoming.id))
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
