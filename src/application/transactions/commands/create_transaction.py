from dataclasses import dataclass
from datetime import date
from typing import cast

from application.dto.transaction_dto import CreateTransactionDTO, TransactionResponseDTO
from domain.entities.transaction import Transaction
from domain.objects.money import Money
from domain.repositories.account_repository import AccountRepository
from domain.repositories.bank_repository import BankRepository
from domain.repositories.category_repository import CategoryRepository
from domain.repositories.transaction_repository import TransactionRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from domain.repositories.user_repository import UserRepository
from shared.exceptions.domain import (
    AccountNotFoundError,
    InvalidTransactionTypeError,
    UserNotFoundError,
)


@dataclass
class CreateTransactionCommand:
    """
    Command for creating a transaction
    """

    dto: CreateTransactionDTO


class CreateTransactionHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        account_repository: AccountRepository,
        transaction_repository: TransactionRepository,
        category_repository: CategoryRepository,
        bank_repository: BankRepository,
        uow: AbstractUnitOfWork,
    ):
        self.user_repository = user_repository
        self.account_repository = account_repository
        self.transaction_repository = transaction_repository
        self.category_repository = category_repository
        self.bank_repository = bank_repository
        self.uow = uow

    async def handle(self, command: CreateTransactionCommand) -> TransactionResponseDTO:
        dto = command.dto
        money = Money(dto.amount, dto.currency)

        transaction_date = dto.transaction_date or date.today()

        user = await self.user_repository.get_by_id(dto.user_id)
        if not user or not user.is_active:
            raise UserNotFoundError()

        async with self.uow:
            account = await self.account_repository.get_by_uuid_and_user_id(
                dto.account_uuid, dto.user_id, for_update=True
            )
            if not account:
                raise AccountNotFoundError(account_uuid=dto.account_uuid)

            transaction = Transaction.create_new(
                user_id=cast(int, user.id),
                account_id=cast(int, account.id),
                category_id=dto.category_id,
                transaction_type=dto.transaction_type,
                amount=money,
                transaction_date=transaction_date,
                description=dto.description,
                notes=dto.notes,
            )

            # Los ingresos van al saldo disponible sin importar el tipo de
            # cuenta; el capital que rinde se maneja por apartado
            # (investment_positions), no a nivel cuenta.
            if transaction.is_expense():
                new_balance = account.current_balance.subtract(money)
            elif transaction.is_income():
                new_balance = account.current_balance.add(money)
            else:
                raise InvalidTransactionTypeError(transaction.transaction_type)

            account.update_balance(new_balance)

            await self.account_repository.update(account)

            category = (
                await self.category_repository.get_by_id(dto.category_id)
                if dto.category_id
                else None
            )
            category_name = category.name if category else None

            transaction = await self.transaction_repository.create(transaction)

            await self.uow.commit()

        return TransactionResponseDTO.from_entity(
            transaction=transaction,
            account_name=account.name,
            account_type=account.account_type,
            account_uuid=cast(str, account.uuid),
            category_name=category_name,
        )
