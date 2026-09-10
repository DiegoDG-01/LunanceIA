from abc import ABC, abstractmethod

from domain.entities.account import Account


class AccountRepository(ABC):
    """Account repository interface"""

    @abstractmethod
    async def create(self, account: Account) -> Account:
        """Create account"""

    @abstractmethod
    async def get_by_id(
        self, account_id: int, *, for_update: bool = False
    ) -> Account | None:
        """Get account by id"""

    @abstractmethod
    async def get_bulk_by_ids(self, account_ids: list[int]) -> list[Account]:
        """Get account by id"""

    @abstractmethod
    async def get_by_uuid_and_user_id(
        self, account_uuid: str, user_id: int, *, for_update: bool = False
    ) -> Account | None:
        """Get account by id and user uuid"""

    @abstractmethod
    async def get_by_user_id(
        self, user_id: int, limit: int, offset: int
    ) -> list[Account]:
        """Get all accounts by user uuid"""

    @abstractmethod
    async def get_active_by_user(
        self, user_id: int, limit: int, offset: int
    ) -> list[Account]:
        """Get all active accounts by user uuid"""

    @abstractmethod
    async def update(self, account: Account) -> Account:
        """Update account"""

    @abstractmethod
    async def switch_status(self, account: Account) -> Account:
        """Switch account status"""

    @abstractmethod
    async def delete(self, account: Account) -> bool:
        """This method is used to completely delete an account"""

    @abstractmethod
    async def get_by_uuid_and_user_id_with_settings(
        self, uuid: str, user_id: int
    ) -> Account | None:
        pass
