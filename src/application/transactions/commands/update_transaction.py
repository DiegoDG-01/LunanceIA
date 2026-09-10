from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import cast

from application.dto.transaction_dto import TransactionResponseDTO
from domain.entities.transaction import TransactionType
from domain.objects.money import Money
from domain.repositories.account_repository import AccountRepository
from domain.repositories.installment_purchase_repository import (
    InstallmentPurchaseRepository,
)
from domain.repositories.transaction_repository import TransactionRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from shared.exceptions.domain import (
    AccountNotFoundError,
    InstallmentTransactionModificationError,
    InvalidTransactionTypeError,
    TransactionNotFoundError,
)


@dataclass
class UpdateTransactionCommand:
    transaction_uuid: str
    user_id: int
    description: str | None = None
    notes: str | None = None
    category_id: int | None = None
    transaction_type: str | None = None
    amount: Decimal | None = None
    transaction_date: date | None = None
    account_uuid: str | None = None


class UpdateTransactionCommandHandler:
    def __init__(
        self,
        transaction_repository: TransactionRepository,
        account_repository: AccountRepository,
        installment_purchase_repository: InstallmentPurchaseRepository,
        uow: AbstractUnitOfWork,
    ):
        self.transaction_repository = transaction_repository
        self.account_repository = account_repository
        self.installment_purchase_repository = installment_purchase_repository
        self.uow = uow

    async def handle(self, command: UpdateTransactionCommand) -> TransactionResponseDTO:
        async with self.uow:
            # Block transaction to avoid race conditions and ensure consistency
            transaction = await self.transaction_repository.get_by_uuid_and_user_id(
                command.transaction_uuid, command.user_id, for_update=True
            )
            if not transaction:
                raise TransactionNotFoundError(command.transaction_uuid)

            purchase = await self.installment_purchase_repository.get_by_initial_transaction_id(
                transaction.id, command.user_id
            )
            if purchase:
                raise InstallmentTransactionModificationError()

            # Una transferencia se compone de dos movimientos y debe editarse
            # mediante su caso de uso específico para no desbalancear cuentas.
            if transaction.is_transfer():
                raise InvalidTransactionTypeError(transaction.transaction_type.value)

            source_account_id = transaction.account_id
            destination_account_id = source_account_id

            if command.account_uuid:
                destination_preview = (
                    await self.account_repository.get_by_uuid_and_user_id(
                        command.account_uuid, command.user_id
                    )
                )
                if not destination_preview:
                    raise AccountNotFoundError(account_uuid=command.account_uuid)

                destination_account_id = destination_preview.id

            locked_accounts = {}

            for account_id in sorted({source_account_id, destination_account_id}):
                locked_account = await self.account_repository.get_by_id(
                    account_id, for_update=True
                )

                if not locked_account or locked_account.user_id != command.user_id:
                    raise AccountNotFoundError(str(account_id))

                locked_accounts[account_id] = locked_account

            account = locked_accounts[source_account_id]
            new_account = locked_accounts[destination_account_id]

            # 1. REVERTIR el efecto de la transacción original
            if transaction.transaction_type == TransactionType.EXPENSE:
                account.update_balance(account.current_balance.add(transaction.amount))
            elif transaction.transaction_type == TransactionType.INCOME:
                account.update_balance(
                    account.current_balance.subtract(transaction.amount)
                )

            # 2. ACTUALIZAR los campos de la transacción
            if command.category_id is not None:
                transaction.category_id = command.category_id

            if destination_account_id != source_account_id:
                transaction.account_id = destination_account_id

            if command.description is not None:
                transaction.description = command.description

            if command.notes is not None:
                transaction.notes = command.notes

            if command.transaction_type is not None:
                try:
                    transaction.transaction_type = TransactionType(
                        command.transaction_type
                    )
                except ValueError:
                    raise InvalidTransactionTypeError(command.transaction_type)

            if command.amount is not None:
                transaction.amount = Money(amount=command.amount, currency="MXN")

            if command.transaction_date is not None:
                if isinstance(command.transaction_date, str):
                    transaction.transaction_date = datetime.strptime(
                        command.transaction_date, "%Y-%m-%d"
                    ).date()
                else:
                    transaction.transaction_date = command.transaction_date

            # 3. APLICAR el efecto de la transacción actualizada
            if transaction.is_expense():
                new_account.update_balance(
                    new_account.current_balance.subtract(transaction.amount)
                )
            elif transaction.is_income():
                new_account.update_balance(
                    new_account.current_balance.add(transaction.amount)
                )

            # 4. GUARDAR ambos: transacción y cuenta

            await self.transaction_repository.update(transaction)
            await self.account_repository.update(account)
            if new_account is not account:
                await self.account_repository.update(new_account)
            await self.uow.commit()

        # 5. OBTENER resultado para respuesta
        result = await self.transaction_repository.get_by_uuid_with_account_details(
            cast(str, transaction.uuid), command.user_id
        )

        if not result:
            raise TransactionNotFoundError(command.transaction_uuid)

        transaction_entity, account_name, account_type, account_uuid, category_name = (
            result
        )

        return TransactionResponseDTO.from_entity(
            transaction_entity,
            account_name,
            account_type,
            cast(str, account_uuid),
            category_name,
        )
