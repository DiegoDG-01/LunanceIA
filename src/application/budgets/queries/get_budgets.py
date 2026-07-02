from dataclasses import dataclass
from typing import Optional, List

from domain.repositories.budget_repository import BudgetRepository
from domain.repositories.category_repository import CategoryRepository
from application.dto.budget_dto import BudgetResponseDTO


@dataclass
class GetBudgetsQuery:
    user_id: int
    active_only: bool = False
    category_id: Optional[int] = None


class GetBudgetsHandler:
    def __init__(
        self,
        budget_repository: BudgetRepository,
        category_repository: CategoryRepository,
    ):
        self.budget_repository = budget_repository
        self.category_repository = category_repository

    async def handle(self, query: GetBudgetsQuery) -> List[BudgetResponseDTO]:
        budgets = await self.budget_repository.get_by_user(
            user_id=query.user_id,
            active_only=query.active_only,
            category_id=query.category_id,
        )

        result = []
        for budget in budgets:
            category_name: Optional[str] = None
            if budget.category_id is not None:
                category = await self.category_repository.get_by_id(budget.category_id)
                category_name = category.name if category else None

            result.append(
                BudgetResponseDTO.from_entity(budget, category_name=category_name)
            )

        return result
