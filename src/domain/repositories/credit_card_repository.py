from abc import ABC, abstractmethod

from domain.objects.credit_card_settings import CreditCardSettings


class CreditCardSettingsRepository(ABC):
    @abstractmethod
    async def create(
        self, account_id: int, settings: CreditCardSettings
    ) -> CreditCardSettings:
        pass

    @abstractmethod
    async def get_by_account_id(self, account_id: int) -> CreditCardSettings | None:
        pass

    @abstractmethod
    async def update(
        self, account_id: int, settings: CreditCardSettings
    ) -> CreditCardSettings:
        pass

    @abstractmethod
    async def delete(self, account_id: int) -> bool:
        pass
