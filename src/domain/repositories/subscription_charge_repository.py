from abc import ABC, abstractmethod
from datetime import date

from domain.entities.subscription_charge import SubscriptionCharge


class SubscriptionChargeRepository(ABC):
    @abstractmethod
    async def create(self, charge: SubscriptionCharge) -> SubscriptionCharge:
        pass

    @abstractmethod
    async def update(self, charge: SubscriptionCharge) -> SubscriptionCharge:
        pass

    @abstractmethod
    async def get_by_id(self, charge_id: int) -> SubscriptionCharge | None:
        pass

    @abstractmethod
    async def get_by_subscription(
        self, subscription_id: int, limit: int = 100, offset: int = 0
    ) -> list[SubscriptionCharge]:
        pass

    @abstractmethod
    async def get_by_subscription_and_month(
        self, subscription_id: int, year: int, month: int
    ) -> SubscriptionCharge | None:
        pass

    @abstractmethod
    async def get_by_subscription_and_date(
        self, subscription_id: int, charge_date: date
    ) -> SubscriptionCharge | None:
        pass

    @abstractmethod
    async def get_pending_charges(self) -> list[SubscriptionCharge]:
        """Get all charges with PENDIENTE status"""

    @abstractmethod
    async def get_last_charges_by_subscription_id(
        self, subscription_id: int
    ) -> list[tuple[SubscriptionCharge, str, str]]:
        pass

    @abstractmethod
    async def get_by_user_with_details(self, user_id: int) -> list[tuple]:
        pass
