from typing import Optional
from datetime import datetime
from dataclasses import dataclass

from domain.objects.money import Money
from domain.entities.transaction import TransactionType
from shared.exceptions.domain import (
    TransactionNotFoundError,
    AccountNotFoundError,
    InvalidTransactionTypeError,
)
from application.dto.transaction_dto import TransactionResponseDTO
from domain.repositories.account_repository import AccountRepository
from domain.repositories.transaction_repository import TransactionRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork


@dataclass
class UpdateTransactionCommand:
    transaction_uuid: str
    user_id: int
    description: Optional[str] = None
    notes: Optional[str] = None
    category_id: Optional[int] = None
    transaction_type: Optional[str] = None
    amount: Optional[float] = None
    transaction_date: Optional[str] = None


class UpdateTransactionCommandHandler:
    def __init__(
        self,
        transaction_repository: TransactionRepository,
        account_repository: AccountRepository,
        uow: AbstractUnitOfWork,
    ):
        self.transaction_repository = transaction_repository
        self.account_repository = account_repository
        self.uow = uow

    async def handle(self, command: UpdateTransactionCommand) -> TransactionResponseDTO:
        transaction = await self.transaction_repository.get_by_uuid_and_user_id(
            command.transaction_uuid, command.user_id
        )
        if not transaction:
            raise TransactionNotFoundError(command.transaction_uuid)

        account = await self.account_repository.get_by_id(transaction.account_id)

        if not account:
            raise AccountNotFoundError(command.user_id)

        # 1. REVERTIR el efecto de la transacción original
        if transaction.transaction_type == TransactionType.EXPENSE:
            account.current_balance = account.current_balance.add(transaction.amount)
        elif transaction.transaction_type == TransactionType.INCOME:
            account.current_balance = account.current_balance.subtract(
                transaction.amount
            )

        # 2. ACTUALIZAR los campos de la transacción
        transaction.category_id = command.category_id

        if command.description is not None:
            transaction.description = command.description

        if command.notes is not None:
            transaction.notes = command.notes

        if command.transaction_type is not None:
            try:
                transaction.transaction_type = TransactionType(command.transaction_type)
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
            account.current_balance = account.current_balance.subtract(
                transaction.amount
            )
        elif transaction.is_income():
            account.current_balance = account.current_balance.add(transaction.amount)

        # 4. GUARDAR ambos: transacción y cuenta
        async with self.uow:
            await self.transaction_repository.update(transaction)
            await self.account_repository.update(account)
            await self.uow.commit()

        # 5. OBTENER resultado para respuesta
        result = await self.transaction_repository.get_by_uuid_with_account_details(
            transaction.uuid, command.user_id
        )

        if not result:
            raise TransactionNotFoundError(command.transaction_uuid)

        transaction_entity, account_name, account_type, account_bank, category_name = (
            result
        )

        return TransactionResponseDTO.from_entity(
            transaction_entity, account_name, account_type, account_bank, category_name
        )
