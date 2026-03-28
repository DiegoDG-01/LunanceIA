from abc import ABC, abstractmethod
from typing import Optional
from domain.objects.investment_settings import InvestmentCardSettings


class InvestmentCardSettingsRepository(ABC):
    @abstractmethod
    async def create(
        self, account_id: int, settings: InvestmentCardSettings
    ) -> InvestmentCardSettings:
        pass

    @abstractmethod
    async def get_by_account_id(
        self, account_id: int
    ) -> Optional[InvestmentCardSettings]:
        pass

    @abstractmethod
    async def update(
        self, account_id: int, settings: InvestmentCardSettings
    ) -> InvestmentCardSettings:
        pass

    @abstractmethod
    async def delete(self, account_id: int) -> bool:
        pass
