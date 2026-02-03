from abc import ABC, abstractmethod
from typing import Optional, List
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
    async def get_by_id(self, charge_id: int) -> Optional[SubscriptionCharge]:
        pass

    @abstractmethod
    async def get_by_subscription(
        self, subscription_id: int, limit: int = 100, offset: int = 0
    ) -> List[SubscriptionCharge]:
        pass

    @abstractmethod
    async def get_by_subscription_and_month(
        self, subscription_id: int, year: int, month: int
    ) -> Optional[SubscriptionCharge]:
        pass

    @abstractmethod
    async def get_by_subscription_and_date(
        self, subscription_id: int, charge_date: date
    ) -> Optional[SubscriptionCharge]:
        pass

    @abstractmethod
    async def get_pending_charges(self) -> List[SubscriptionCharge]:
        """Get all charges with PENDIENTE status"""
        pass
