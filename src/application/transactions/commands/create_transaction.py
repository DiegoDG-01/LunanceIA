import dataclasses
from dataclasses import dataclass

from datetime import date

from domain.objects.enums import AccountType
from domain.objects.money import Money
from domain.entities.transaction import Transaction
from shared.exceptions.domain import AccountNotFoundError
from shared.exceptions.domain import UserNotFoundError
from domain.repositories.user_repository import UserRepository
from domain.repositories.account_repository import AccountRepository
from domain.repositories.category_repository import CategoryRepository
from domain.repositories.transaction_repository import TransactionRepository
from domain.repositories.bank_repository import BankRepository
from application.dto.transaction_dto import CreateTransactionDTO, TransactionResponseDTO
from shared.exceptions.domain import InvalidTransactionTypeError
from domain.repositories.investment_card_repository import (
    InvestmentCardSettingsRepository,
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
        investment_settings_repository: InvestmentCardSettingsRepository,
    ):
        self.user_repository = user_repository
        self.account_repository = account_repository
        self.transaction_repository = transaction_repository
        self.category_repository = category_repository
        self.bank_repository = bank_repository
        self.investment_settings_repository = investment_settings_repository

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
            raise AccountNotFoundError(account_uuid=dto.account_uuid)

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
            if account.account_type is AccountType.INVESTMENT:
                settings = await self.investment_settings_repository.get_by_account_id(
                    account_id=account.id
                )
                updated_settings = dataclasses.replace(
                    settings,
                    base_principal=(
                        settings.base_principal or account.current_balance.amount
                    )
                    + money.amount,
                )
                await self.investment_settings_repository.update(
                    account_id=account.id, settings=updated_settings
                )

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

        bank_name = None
        if account.bank_id:
            bank = await self.bank_repository.get_by_id(account.bank_id)
            bank_name = bank.name if bank else None

        return TransactionResponseDTO.from_entity(
            transaction,
            account.name,
            account.account_type,
            bank_name,
            category_name,
        )
