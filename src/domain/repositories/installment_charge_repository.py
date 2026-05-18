from abc import ABC, abstractmethod
from typing import List, Optional

from domain.entities.installment_charge import InstallmentCharge


class InstallmentChargeRepository(ABC):
    @abstractmethod
    async def create_bulk(
        self, charges: List[InstallmentCharge]
    ) -> List[InstallmentCharge]:
        pass

    @abstractmethod
    async def get_by_uuid(self, uuid: str) -> Optional[InstallmentCharge]:
        pass

    @abstractmethod
    async def get_by_purchase_id(self, purchase_id: int) -> List[InstallmentCharge]:
        pass

    @abstractmethod
    async def get_bulk_by_purchase_ids(
        self, purchase_ids: List[int]
    ) -> List[InstallmentCharge]:
        pass

    @abstractmethod
    async def get_pending_charges(self, user_id: int) -> List[InstallmentCharge]:
        pass

    @abstractmethod
    async def update(self, charge: InstallmentCharge) -> InstallmentCharge:
        pass

    @abstractmethod
    async def delete_by_purchase_id(self, purchase_id: int) -> None:
        pass
