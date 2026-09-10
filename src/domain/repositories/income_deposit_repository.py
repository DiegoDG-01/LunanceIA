from abc import ABC, abstractmethod
from datetime import date

from domain.entities.income_deposit import IncomeDeposit


class IncomeDepositRepository(ABC):
    @abstractmethod
    async def create(self, deposit: IncomeDeposit) -> IncomeDeposit:
        pass

    @abstractmethod
    async def update(self, deposit: IncomeDeposit) -> IncomeDeposit:
        pass

    @abstractmethod
    async def get_by_income(
        self, recurring_income_id: int, limit: int = 100, offset: int = 0
    ) -> list[tuple[IncomeDeposit, str | None]]:
        """Get deposits for a recurring income with their transaction uuid,
        most recent first"""

    @abstractmethod
    async def get_by_income_and_date(
        self, recurring_income_id: int, deposit_date: date
    ) -> IncomeDeposit | None:
        """Get deposit for a recurring income on an exact date (idempotency check)"""
