from abc import ABC, abstractmethod
from datetime import date
from typing import Optional, List

from domain.entities.recurring_income import RecurringIncome


class RecurringIncomeRepository(ABC):
    @abstractmethod
    async def create(self, income: RecurringIncome) -> RecurringIncome:
        """Create recurring income"""
        pass

    @abstractmethod
    async def update(self, income: RecurringIncome) -> RecurringIncome:
        """Update recurring income"""
        pass

    @abstractmethod
    async def delete(self, uuid: str, user_id: int) -> bool:
        """
        Delete recurring income by UUID with ownership validation.

        Returns:
            bool: True if deleted, False if not found or access denied
        """
        pass

    @abstractmethod
    async def get_by_uuid_and_user_id(
        self, income_uuid: str, user_id: int
    ) -> Optional[RecurringIncome]:
        """Get recurring income by uuid"""
        pass

    @abstractmethod
    async def get_by_account(
        self, account_uuid: str, user_id: int, limit: int = 100, offset: int = 0
    ) -> List[RecurringIncome]:
        """Get recurring incomes by account"""
        pass

    @abstractmethod
    async def get_by_category(
        self,
        user_id: int,
        category_id: int,
    ) -> List[RecurringIncome]:
        """Get recurring incomes by category"""
        pass

    @abstractmethod
    async def get_by_user(
        self, user_id: int, active_only: bool = False
    ) -> List[RecurringIncome]:
        """Get all recurring incomes for a user, optionally filter by active status"""
        pass

    @abstractmethod
    async def get_due_incomes(self, as_of: date) -> List[RecurringIncome]:
        """Get active recurring incomes with next_payment_date on or before as_of"""
        pass

    @abstractmethod
    async def switch_status(self, income: RecurringIncome) -> RecurringIncome:
        """Switch recurring income status"""
        pass
