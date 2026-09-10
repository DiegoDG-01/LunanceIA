from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal

from domain.entities.budget import Budget


class BudgetRepository(ABC):
    @abstractmethod
    async def create(self, budget: Budget) -> Budget:
        """Create a new budget."""

    @abstractmethod
    async def update(self, budget: Budget) -> Budget:
        """Update an existing budget."""

    @abstractmethod
    async def delete(self, uuid: str, user_id: int) -> bool:
        """
        Delete a budget by UUID with ownership validation.

        Returns:
            bool: True if deleted, False if not found or access denied.
        """

    @abstractmethod
    async def get_by_uuid_and_user_id(
        self, budget_uuid: str, user_id: int
    ) -> Budget | None:
        """Get a budget by its UUID ensuring it belongs to the user."""

    @abstractmethod
    async def get_by_user(
        self,
        user_id: int,
        active_only: bool = False,
        category_id: int | None = None,
    ) -> list[Budget]:
        """Get all budgets for a user with optional filters."""

    @abstractmethod
    async def switch_status(self, budget: Budget) -> Budget:
        """Toggle is_active status of a budget."""

    @abstractmethod
    async def get_spending_for_period(
        self,
        user_id: int,
        period_start: date,
        period_end: date,
        category_id: int | None = None,
    ) -> Decimal:
        """
        Returns the total EXPENSE amount for the user in the given date range,
        optionally filtered by category.
        """
