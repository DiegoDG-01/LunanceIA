from dataclasses import dataclass
from typing import cast

from application.dto.recurring_income_dto import (
    UpdateRecurringIncomeDTO,
    RecurringIncomeResponseDTO,
)
from domain.objects.money import Money
from domain.repositories.recurring_income_repository import RecurringIncomeRepository
from domain.repositories.category_repository import CategoryRepository
from domain.repositories.account_repository import AccountRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from shared.exceptions.domain import (
    CategoryNotFoundError,
    AccountNotFoundError,
    RecurringIncomeNotFoundError,
    InvalidIncomeDateRangeError,
)


@dataclass
class UpdateRecurringIncomeCommand:
    income_uuid: str
    user_id: int
    dto: UpdateRecurringIncomeDTO


class UpdateRecurringIncomeHandler:
    def __init__(
        self,
        recurring_income_repository: RecurringIncomeRepository,
        category_repository: CategoryRepository,
        account_repository: AccountRepository,
        uow: AbstractUnitOfWork,
    ):
        self.recurring_income = recurring_income_repository
        self.category_repository = category_repository
        self.account_repository = account_repository
        self.uow = uow

    async def handle(
        self, command: UpdateRecurringIncomeCommand
    ) -> RecurringIncomeResponseDTO:
        dto = command.dto

        income = await self.recurring_income.get_by_uuid_and_user_id(
            command.income_uuid, command.user_id
        )

        if not income:
            raise RecurringIncomeNotFoundError(command.income_uuid)

        if dto.category_id is not None:
            category = await self.category_repository.get_by_id(dto.category_id)
            if not category:
                raise CategoryNotFoundError(dto.category_id)

        if dto.account_uuid is not None:
            account = await self.account_repository.get_by_uuid_and_user_id(
                account_uuid=dto.account_uuid, user_id=command.user_id
            )
            if not account:
                raise AccountNotFoundError(dto.account_uuid)

            income.account_id = cast(int, account.id)

        if dto.category_id is not None:
            income.category_id = dto.category_id
        if dto.name is not None:
            income.name = dto.name
        if dto.amount is not None:
            income.amount = Money(dto.amount, currency=income.amount.currency)
        if dto.frequency is not None:
            income.frequency = dto.frequency
        if dto.start_date is not None:
            income.start_date = dto.start_date
        if dto.end_date is not None:
            income.end_date = dto.end_date
        if dto.next_payment_date is not None:
            income.next_payment_date = dto.next_payment_date
        if dto.is_active is not None:
            income.is_active = dto.is_active
        if dto.description is not None:
            income.description = dto.description

        if income.end_date is not None and income.end_date < income.start_date:
            raise InvalidIncomeDateRangeError(
                str(income.start_date), str(income.end_date)
            )

        async with self.uow:
            updated_income = await self.recurring_income.update(income)
            await self.uow.commit()

        account = await self.account_repository.get_by_id(income.account_id)
        account_uuid = account.uuid if account else None
        account_name = account.name if account else None

        category = (
            await self.category_repository.get_by_id(income.category_id)
            if updated_income.category_id
            else None
        )
        category_name = category.name if category else None

        return RecurringIncomeResponseDTO.from_entity(
            updated_income, account_uuid, account_name, category_name
        )
