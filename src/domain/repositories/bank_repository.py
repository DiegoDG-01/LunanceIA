from abc import ABC, abstractmethod
from typing import Optional, List
from domain.entities.bank import Bank


class BankRepository(ABC):
    @abstractmethod
    async def get_all(self) -> List[Bank]:
        pass

    @abstractmethod
    async def get_by_id(self, bank_id: int) -> Optional[Bank]:
        pass

    @abstractmethod
    async def get_by_code(self, bank_code: str) -> Optional[Bank]:
        pass

    @abstractmethod
    async def create(self, bank: Bank) -> Bank:
        pass

    @abstractmethod
    async def update(self, bank: Bank) -> Bank:
        pass

    @abstractmethod
    async def delete(self, bank_id: int) -> None:
        pass
