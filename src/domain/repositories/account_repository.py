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
    async def get_by_id_and_user_id(self, account_id: int, user_id: int) -> Optional[Account]:
        """Get account by id and user uuid"""
        pass

    @abstractmethod
    async def get_by_user_id(self, user_id: int) -> List[Account]:
        """Get all accounts by user uuid"""
        pass

    @abstractmethod
    async def get_active_by_user(self, user_id: str) -> List[Account]:
        """ Get all active accounts by user uuid"""
        pass

    @abstractmethod
    async def update(self, account: Account) -> Account:
        """Update account"""
        pass

    @abstractmethod
    async def deactivate(self, account: Account) -> Account:
        """This method is used to soft delete an account"""
        pass

    @abstractmethod
    async def activate(self, account: Account) -> Account:
        """This method is used to activate an account"""
        pass

    @abstractmethod
    async def delete(self, account: Account) -> Account:
        """This method is used to completely delete an account"""
        pass