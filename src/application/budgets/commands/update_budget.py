from dataclasses import dataclass

from application.dto.budget_dto import BudgetResponseDTO, UpdateBudgetDTO
from domain.repositories.budget_repository import BudgetRepository
from domain.repositories.category_repository import CategoryRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from shared.exceptions.domain import BudgetNotFoundError, CategoryNotFoundError


@dataclass
class UpdateBudgetCommand:
    budget_uuid: str
    user_id: int
    dto: UpdateBudgetDTO


class UpdateBudgetHandler:
    def __init__(
        self,
        budget_repository: BudgetRepository,
        category_repository: CategoryRepository,
        uow: AbstractUnitOfWork,
    ):
        self.budget_repository = budget_repository
        self.category_repository = category_repository
        self.uow = uow

    async def handle(self, command: UpdateBudgetCommand) -> BudgetResponseDTO:
        dto = command.dto

        budget = await self.budget_repository.get_by_uuid_and_user_id(
            command.budget_uuid, command.user_id
        )
        if not budget:
            raise BudgetNotFoundError(command.budget_uuid)

        category_name: str | None = None

        if dto.category_id is not None:
            category = await self.category_repository.get_by_id(dto.category_id)
            if not category:
                raise CategoryNotFoundError(dto.category_id)
            category_name = category.name
            budget.category_id = dto.category_id
        elif budget.category_id is not None:
            category = await self.category_repository.get_by_id(budget.category_id)
            category_name = category.name if category else None

        if dto.name is not None:
            budget.name = dto.name
        if dto.limit_amount is not None:
            budget.limit_amount = dto.limit_amount
        if dto.period is not None:
            budget.period = dto.period
        if dto.start_date is not None:
            budget.start_date = dto.start_date
        if dto.end_date is not None:
            budget.end_date = dto.end_date
        if dto.alert_percentage is not None:
            budget.alert_percentage = dto.alert_percentage

        async with self.uow:
            updated_budget = await self.budget_repository.update(budget)
            await self.uow.commit()

        return BudgetResponseDTO.from_entity(
            updated_budget, category_name=category_name
        )
