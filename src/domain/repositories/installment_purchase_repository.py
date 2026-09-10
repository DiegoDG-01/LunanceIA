from abc import ABC, abstractmethod

from domain.entities.installment_purchase import InstallmentPurchase


class InstallmentPurchaseRepository(ABC):
    @abstractmethod
    async def create(self, purchase: InstallmentPurchase) -> InstallmentPurchase:
        pass

    @abstractmethod
    async def get_by_id(
        self, purchase_id: int, *, for_update: bool = False
    ) -> InstallmentPurchase | None:
        pass

    @abstractmethod
    async def get_by_uuid(
        self, uuid: str, user_id, *, for_update: bool = False
    ) -> InstallmentPurchase | None:
        pass

    @abstractmethod
    async def get_by_initial_transaction_id(
        self, transaction_id: int, user_id: int
    ) -> InstallmentPurchase | None:
        """Return the installment purchase created by an initial expense."""

    @abstractmethod
    async def get_all_by_user_id(self, user_id: int) -> list[InstallmentPurchase]:
        pass

    @abstractmethod
    async def update(self, purchase: InstallmentPurchase) -> InstallmentPurchase:
        pass

    @abstractmethod
    async def delete(self, purchase_uuid: str) -> bool:
        pass
