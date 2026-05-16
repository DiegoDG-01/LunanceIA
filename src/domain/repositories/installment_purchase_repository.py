from abc import ABC, abstractmethod
from typing import Optional, List

from domain.entities.installment_purchase import InstallmentPurchase


class InstallmentPurchaseRepository(ABC):
    @abstractmethod
    async def create(self, purchase: InstallmentPurchase) -> InstallmentPurchase:
        pass

    @abstractmethod
    async def get_by_id(self, purchase_id: int) -> Optional[InstallmentPurchase]:
        pass

    @abstractmethod
    async def get_by_uuid(self, uuid: str, user_id) -> Optional[InstallmentPurchase]:
        pass

    @abstractmethod
    async def get_all_by_user_id(self, user_id: int) -> List[InstallmentPurchase]:
        pass

    @abstractmethod
    async def update(self, purchase: InstallmentPurchase) -> InstallmentPurchase:
        pass

    @abstractmethod
    async def delete(self, purchase_id: int) -> bool:
        pass