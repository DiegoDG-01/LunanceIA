from dataclasses import dataclass
from typing import Optional

from domain.repositories.budget_repository import BudgetRepository
from domain.repositories.category_repository import CategoryRepository
from application.dto.budget_dto import BudgetResponseDTO
from shared.exceptions.domain import BudgetNotFoundError


@dataclass
class GetBudgetByIdQuery:
    budget_uuid: str
    user_id: int


class GetBudgetByIdHandler:
    def __init__(
        self,
        budget_repository: BudgetRepository,
        category_repository: CategoryRepository,
    ):
        self.budget_repository = budget_repository
        self.category_repository = category_repository

    async def handle(self, query: GetBudgetByIdQuery) -> BudgetResponseDTO:
        budget = await self.budget_repository.get_by_uuid_and_user_id(
            query.budget_uuid, query.user_id
        )
        if not budget:
            raise BudgetNotFoundError(query.budget_uuid)

        category_name: Optional[str] = None
        if budget.category_id is not None:
            category = await self.category_repository.get_by_id(budget.category_id)
            category_name = category.name if category else None

        return BudgetResponseDTO.from_entity(budget, category_name=category_name)
