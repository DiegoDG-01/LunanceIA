from abc import ABC, abstractmethod

from domain.entities.installment_charge import InstallmentCharge


class InstallmentChargeRepository(ABC):
    @abstractmethod
    async def create_bulk(
        self, charges: list[InstallmentCharge]
    ) -> list[InstallmentCharge]:
        pass

    @abstractmethod
    async def get_by_uuid(
        self, uuid: str, *, for_update: bool = False
    ) -> InstallmentCharge | None:
        pass

    @abstractmethod
    async def get_by_transaction_id(
        self, transaction_id: int
    ) -> InstallmentCharge | None:
        """Return the installment charge paid by a transaction, if any."""

    @abstractmethod
    async def get_by_purchase_id(
        self, purchase_id: int, *, for_update: bool = False
    ) -> list[InstallmentCharge]:
        pass

    @abstractmethod
    async def get_bulk_by_purchase_ids(
        self, purchase_ids: list[int]
    ) -> list[InstallmentCharge]:
        pass

    @abstractmethod
    async def get_pending_charges(self, user_id: int) -> list[InstallmentCharge]:
        pass

    @abstractmethod
    async def update(self, charge: InstallmentCharge) -> InstallmentCharge:
        pass

    @abstractmethod
    async def delete_by_purchase_id(self, purchase_id: int) -> None:
        pass
