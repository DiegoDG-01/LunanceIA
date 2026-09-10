from abc import ABC, abstractmethod
from datetime import date

from domain.entities.investment_yield import InvestmentYield


class InvestmentYieldRepository(ABC):
    @abstractmethod
    async def create(self, yield_record: InvestmentYield) -> InvestmentYield:
        pass

    @abstractmethod
    async def get_by_account_id(
        self, account_id: int, limit: int = 365, offset: int = 0
    ) -> list[InvestmentYield]:
        pass

    @abstractmethod
    async def get_by_account_and_date(
        self, account_id: int, yield_date: date
    ) -> InvestmentYield | None:
        pass

    @abstractmethod
    async def get_first_by_account_id(
        self,
        account_id: int,
    ) -> InvestmentYield | None:
        pass

    @abstractmethod
    async def get_by_position_id(
        self, position_id: int, limit: int = 365, offset: int = 0
    ) -> list[InvestmentYield]:
        pass

    @abstractmethod
    async def get_by_position_and_date(
        self, position_id: int, yield_date: date
    ) -> InvestmentYield | None:
        pass
