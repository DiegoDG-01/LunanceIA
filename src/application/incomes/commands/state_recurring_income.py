from dataclasses import dataclass

from application.dto.recurring_income_dto import RecurringIncomeResponseDTO
from domain.repositories.account_repository import AccountRepository
from domain.repositories.category_repository import CategoryRepository
from domain.repositories.recurring_income_repository import RecurringIncomeRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork

from shared.exceptions.domain import (
    RecurringIncomeNotFoundError,
)


@dataclass
class StateRecurringIncomeCommand:
    income_uuid: str
    user_id: int


class StateRecurringIncomeHandler:
    def __init__(
        self,
        recurring_income_repository: RecurringIncomeRepository,
        category_repository: CategoryRepository,
        account_repository: AccountRepository,
        uow: AbstractUnitOfWork,
    ):
        self.recurring_income_repository = recurring_income_repository
        self.category_repository = category_repository
        self.account_repository = account_repository
        self.uow = uow

    async def handle(
        self, command: StateRecurringIncomeCommand
    ) -> RecurringIncomeResponseDTO:
        income = await self.recurring_income_repository.get_by_uuid_and_user_id(
            command.income_uuid, command.user_id
        )
        if not income:
            raise RecurringIncomeNotFoundError(command.income_uuid)

        account = await self.account_repository.get_by_id(income.account_id)
        account_uuid = account.uuid if account else None
        account_name = account.name if account else None

        category = (
            await self.category_repository.get_by_id(income.category_id)
            if income.category_id
            else None
        )
        category_name = category.name if category else None

        async with self.uow:
            updated_income = await self.recurring_income_repository.switch_status(
                income
            )
            await self.uow.commit()

        return RecurringIncomeResponseDTO.from_entity(
            updated_income, account_uuid, account_name, category_name
        )
