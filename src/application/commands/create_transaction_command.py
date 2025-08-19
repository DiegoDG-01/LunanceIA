from dataclasses import dataclass

from datetime import date
from domain.objects.money import Money
from domain.entities.transaction import Transaction
from shared.exceptions.domain import AccountNotFoundError
from shared.exceptions.domain import UserNotFoundError
from domain.repositories.user_repository import UserRepository
from domain.repositories.account_repository import AccountRepository
from domain.repositories.transaction_repository import TransactionRepository
from application.dto.transaction_dto import CreateTransactionDTO, TransactionResponseDTO


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
    ):
        self.user_repository = user_repository
        self.account_repository = account_repository
        self.transaction_repository = transaction_repository

    async def handle(self, command: CreateTransactionCommand) -> TransactionResponseDTO:
        dto = command.dto
        money = Money(dto.amount, dto.currency)

        transaction_date = dto.transaction_date or date.today()

        user = await self.user_repository.get_by_id(dto.user_id)
        if not user or not user.is_active:
            raise UserNotFoundError()

        account = await self.account_repository.get_by_uuid_and_user_id(
            dto.account_uuid, dto.user_id
        )
        if not account:
            raise AccountNotFoundError(account_id=dto.account_uuid)

        transaction = Transaction.create_new(
            user_id=user.id,
            account_id=account.id,
            category_id=dto.category_id,
            transaction_type=dto.transaction_type,
            amount=money,
            transaction_date=transaction_date,
            description=dto.description,
            notes=dto.notes,
        )

        if transaction.is_expense():
            new_balance = account.current_balance.subtract(money)
        elif transaction.is_income():
            new_balance = account.current_balance.add(money)
        else:
            raise Exception("Invalid transaction type")

        account.update_balance(new_balance)

        await self.account_repository.update(account)

        transaction = self.transaction_repository.create(transaction)

        return TransactionResponseDTO.from_entity(
            transaction,
            account.name,
            account.account_type,
            account.bank,
        )
