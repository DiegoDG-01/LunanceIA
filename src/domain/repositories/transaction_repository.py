from abc import ABC, abstractmethod
from datetime import date

from domain.entities.transaction import Transaction
from domain.objects.enums import AccountType, TransactionType


class TransactionRepository(ABC):
    """
    Interface for transaction repository
    """

    @abstractmethod
    async def create(self, transaction: Transaction) -> Transaction:
        """Create transaction"""

    @abstractmethod
    async def get_by_id(
        self, transaction_id: int, *, for_update: bool = False
    ) -> Transaction | None:
        """Get transaction by id"""

    @abstractmethod
    async def delete_by_uuid(self, uuid: str, user_id: int) -> bool:
        """
        Delete transaction by UUID with ownership validation.

        Returns:
            bool: True if deleted, False if not found or access denied
        """

    @abstractmethod
    async def delete_bulk_by_ids(
        self, transaction_ids: list[int], user_id: int
    ) -> bool:
        pass

    @abstractmethod
    async def get_by_id_and_user_uuid(
        self, transaction_id: int, user_id: int
    ) -> Transaction | None:
        """Get transaction by id and user uuid"""

    @abstractmethod
    async def get_by_account(
        self, account_id: int, user_id: int, limit: int = 100, offset: int = 0
    ) -> list[Transaction]:
        """Get transactions by account id and user uuid"""

    @abstractmethod
    async def get_by_date_range(
        self,
        user_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
        account_uuid: str | None = None,
        transaction_type: TransactionType | None = None,
    ) -> list[tuple[Transaction, str, AccountType, str | None, str | None]]:
        """Get transactions by date range and user uuid"""

    @abstractmethod
    async def get_by_uuid_with_account_details(
        self, uuid: str, user_id: int
    ) -> tuple[Transaction, str, AccountType, str | None, str | None] | None:
        """Get transaction by uuid and user id with account details (name, type, bank)"""

    @abstractmethod
    async def get_by_user(
        self, user_id: int, limit: int = 100, offset: int = 0
    ) -> list[tuple[Transaction, str, AccountType, str | None, str | None]]:
        """Get transactions by user uuid"""

    @abstractmethod
    async def get_by_category(
        self,
        user_id: int,
        category_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Transaction]:
        """Get transactions by category id and user uuid"""

    @abstractmethod
    async def get_by_type(
        self,
        user_id: int,
        transaction_type: TransactionType,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Transaction]:
        """Get transactions by transaction type and user uuid"""

    @abstractmethod
    async def update(self, transaction: Transaction) -> Transaction | None:
        """Update transaction"""

    @abstractmethod
    async def get_by_uuid_and_user_id(
        self, uuid: str, user_id: int, *, for_update: bool = False
    ) -> Transaction | None:
        """Get transaction by UUID and user ID for ownership validation"""

    # @abstractmethod
    # async def delete(self, transaction: Transaction):
    #     """Delete transaction"""
    #     pass

    @abstractmethod
    async def get_total_by_type(
        self,
        user_id: int,
        transaction_type: TransactionType,
        start_date: date | None = None,
        end_date: date | None = None,
        account_id: int | None = None,
    ) -> float:
        """Get total amount by transaction type and user uuid"""

    @abstractmethod
    async def get_monthly_summary(
        self, user_id: int, year: int, month: int, account_id: int | None = None
    ) -> dict:
        """Get monthly summary by user uuid"""

    @abstractmethod
    async def count_by_user(self, user_id: int) -> int:
        """Count transactions by user uuid"""

    @abstractmethod
    async def get_activity_by_account_id(
        self, account_id: int, limit: int = 5
    ) -> list[tuple[Transaction, str | None]]:
        """Get transactions by account id and user uuid
        The limit is a default value of 5
        """

    @abstractmethod
    async def get_filtered(
        self,
        user_id: int,
        account_uuid: str | None = None,
        transaction_type: TransactionType | None = None,
        category_id: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[tuple[Transaction, str, AccountType, str | None, str | None]]:
        pass

    @abstractmethod
    async def get_by_transfer_uuid(
        self, transfer_uuid: str, user_id: int, *, for_update: bool = False
    ) -> list[Transaction]:
        """Get transfer by transfer uuid"""
