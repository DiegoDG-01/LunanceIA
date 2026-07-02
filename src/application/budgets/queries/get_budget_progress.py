from dataclasses import dataclass
from typing import Optional

from domain.repositories.budget_repository import BudgetRepository
from domain.repositories.category_repository import CategoryRepository
from application.dto.budget_dto import BudgetProgressDTO
from shared.exceptions.domain import BudgetNotFoundError


@dataclass
class GetBudgetProgressQuery:
    budget_uuid: str
    user_id: int


class GetBudgetProgressHandler:
    def __init__(
        self,
        budget_repository: BudgetRepository,
        category_repository: CategoryRepository,
    ):
        self.budget_repository = budget_repository
        self.category_repository = category_repository

    async def handle(self, query: GetBudgetProgressQuery) -> BudgetProgressDTO:
        budget = await self.budget_repository.get_by_uuid_and_user_id(
            query.budget_uuid, query.user_id
        )
        if not budget:
            raise BudgetNotFoundError(query.budget_uuid)

        category_name: Optional[str] = None
        if budget.category_id is not None:
            category = await self.category_repository.get_by_id(budget.category_id)
            category_name = category.name if category else None

        period_start, period_end = budget.get_current_period_dates()

        spent_amount = await self.budget_repository.get_spending_for_period(
            user_id=query.user_id,
            period_start=period_start,
            period_end=period_end,
            category_id=budget.category_id,
        )

        remaining = budget.limit_amount - spent_amount
        percentage_used = budget.calculate_percentage_used(spent_amount)
        is_alert = budget.is_alert_triggered(spent_amount)
        is_exceeded = spent_amount > budget.limit_amount

        return BudgetProgressDTO(
            uuid=budget.uuid,
            name=budget.name,
            category_id=budget.category_id,
            category_name=category_name,
            limit_amount=budget.limit_amount,
            spent_amount=spent_amount,
            remaining_amount=remaining,
            percentage_used=round(percentage_used, 2),
            alert_percentage=budget.alert_percentage,
            is_alert_triggered=is_alert,
            is_limit_exceeded=is_exceeded,
            period=budget.period,
            period_start=period_start,
            period_end=period_end,
            is_active=budget.is_active,
        )
