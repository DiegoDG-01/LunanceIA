from abc import ABC, abstractmethod
from typing import Optional, List

from domain.entities.account import Account


class AccountRepository(ABC):
    """Account repository interface"""

    @abstractmethod
    async def create(self, account: Account) -> Account:
        """Create account"""
        pass

    @abstractmethod
    async def get_by_id(self, id: int) -> Optional[Account]:
        """Get account by id"""
        pass

    @abstractmethod
    async def get_by_uuid_and_user_id(
        self, account_uuid: str, user_id: int
    ) -> Optional[Account]:
        """Get account by id and user uuid"""
        pass

    @abstractmethod
    async def get_by_user_id(self, user_id: int) -> List[Account]:
        """Get all accounts by user uuid"""
        pass

    @abstractmethod
    async def get_active_by_user(self, user_uuid: str) -> List[Account]:
        """Get all active accounts by user uuid"""
        pass

    @abstractmethod
    async def update(self, account: Account) -> Account:
        """Update account"""
        pass

    @abstractmethod
    async def switch_status(self, account: Account) -> Account:
        """Switch account status"""
        pass

    @abstractmethod
    async def delete(self, account: Account) -> bool:
        """This method is used to completely delete an account"""
        pass
