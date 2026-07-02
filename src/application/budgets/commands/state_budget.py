from dataclasses import dataclass
from typing import Optional

from domain.repositories.budget_repository import BudgetRepository
from domain.repositories.category_repository import CategoryRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from application.dto.budget_dto import BudgetResponseDTO
from shared.exceptions.domain import BudgetNotFoundError


@dataclass
class StateBudgetCommand:
    budget_uuid: str
    user_id: int


class StateBudgetHandler:
    def __init__(
        self,
        budget_repository: BudgetRepository,
        category_repository: CategoryRepository,
        uow: AbstractUnitOfWork,
    ):
        self.budget_repository = budget_repository
        self.category_repository = category_repository
        self.uow = uow

    async def handle(self, command: StateBudgetCommand) -> BudgetResponseDTO:
        budget = await self.budget_repository.get_by_uuid_and_user_id(
            command.budget_uuid, command.user_id
        )
        if not budget:
            raise BudgetNotFoundError(command.budget_uuid)

        category_name: Optional[str] = None
        if budget.category_id is not None:
            category = await self.category_repository.get_by_id(budget.category_id)
            category_name = category.name if category else None

        async with self.uow:
            updated_budget = await self.budget_repository.switch_status(budget)
            await self.uow.commit()

        return BudgetResponseDTO.from_entity(updated_budget, category_name=category_name)
