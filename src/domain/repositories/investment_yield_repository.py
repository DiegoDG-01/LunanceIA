from abc import ABC, abstractmethod
from datetime import datetime, date
from typing import Optional, List

from domain.entities.investment_yield import InvestmentYield


class InvestmentYieldRepository(ABC):

    @abstractmethod
    async def create(self, yield_record: InvestmentYield) -> InvestmentYield:
        pass

    @abstractmethod
    async def get_by_account_id(
        self, account_id: int, limit: int = 365, offset: int = 0
    ) -> List[InvestmentYield]:
        pass

    @abstractmethod
    async def get_by_account_and_date(
        self, account_id: int, yield_date: date
    ) -> Optional[InvestmentYield]:
        pass

    @abstractmethod
    async def get_first_by_account_id(
        self, account_id: int,
    ) -> Optional[InvestmentYield]:
        pass