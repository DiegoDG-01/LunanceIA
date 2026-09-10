from abc import ABC, abstractmethod
from datetime import date

from domain.entities.recurring_income import RecurringIncome


class RecurringIncomeRepository(ABC):
    @abstractmethod
    async def create(self, income: RecurringIncome) -> RecurringIncome:
        """Create recurring income"""

    @abstractmethod
    async def update(self, income: RecurringIncome) -> RecurringIncome:
        """Update recurring income"""

    @abstractmethod
    async def delete(self, uuid: str, user_id: int) -> bool:
        """
        Delete recurring income by UUID with ownership validation.

        Returns:
            bool: True if deleted, False if not found or access denied
        """

    @abstractmethod
    async def get_by_uuid_and_user_id(
        self, income_uuid: str, user_id: int
    ) -> RecurringIncome | None:
        """Get recurring income by uuid"""

    @abstractmethod
    async def get_by_account(
        self, account_uuid: str, user_id: int, limit: int = 100, offset: int = 0
    ) -> list[RecurringIncome]:
        """Get recurring incomes by account"""

    @abstractmethod
    async def get_by_category(
        self,
        user_id: int,
        category_id: int,
    ) -> list[RecurringIncome]:
        """Get recurring incomes by category"""

    @abstractmethod
    async def get_by_user(
        self, user_id: int, active_only: bool = False
    ) -> list[RecurringIncome]:
        """Get all recurring incomes for a user, optionally filter by active status"""

    @abstractmethod
    async def get_due_incomes(self, as_of: date) -> list[RecurringIncome]:
        """Get active recurring incomes with next_payment_date on or before as_of"""

    @abstractmethod
    async def switch_status(self, income: RecurringIncome) -> RecurringIncome:
        """Switch recurring income status"""
