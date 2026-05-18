from abc import ABC, abstractmethod
from typing import Optional, List, Tuple
from datetime import date

from domain.entities.transaction import Transaction
from domain.objects.enums import TransactionType, AccountType


class TransactionRepository(ABC):
    """
    Interface for transaction repository
    """

    @abstractmethod
    async def create(self, transaction: Transaction) -> Transaction:
        """Create transaction"""
        pass

    @abstractmethod
    async def get_by_id(self, transaction_id: int) -> Optional[Transaction]:
        """Get transaction by id"""
        pass

    @abstractmethod
    async def delete_by_uuid(self, uuid: str, user_id: int) -> bool:
        """
        Delete transaction by UUID with ownership validation.

        Returns:
            bool: True if deleted, False if not found or access denied
        """

    pass

    @abstractmethod
    async def delete_bulk_by_ids(
        self, transaction_ids: list[int], user_id: int
    ) -> bool:
        pass

    @abstractmethod
    async def get_by_id_and_user_uuid(
        self, transaction_id: int, user_id: int
    ) -> Optional[Transaction]:
        """Get transaction by id and user uuid"""
        pass

    @abstractmethod
    async def get_by_account(
        self, account_id: int, user_id: int, limit: int = 100, offset: int = 0
    ) -> List[Transaction]:
        """Get transactions by account id and user uuid"""
        pass

    @abstractmethod
    async def get_by_date_range(
        self,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        account_uuid: Optional[str] = None,
        transaction_type: Optional[TransactionType] = None,
    ) -> List[Tuple[Transaction, str, AccountType, Optional[str], Optional[str]]]:
        """Get transactions by date range and user uuid"""
        pass

    @abstractmethod
    async def get_by_uuid_with_account_details(
        self, uuid: str, user_id: int
    ) -> Optional[Tuple[Transaction, str, AccountType, Optional[str], Optional[str]]]:
        """Get transaction by uuid and user id with account details (name, type, bank)"""
        pass

    @abstractmethod
    async def get_by_user(
        self, user_id: int, limit: int = 100, offset: int = 0
    ) -> List[Tuple[Transaction, str, AccountType, Optional[str], Optional[str]]]:
        """Get transactions by user uuid"""
        pass

    @abstractmethod
    async def get_by_category(
        self,
        user_id: int,
        category_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Transaction]:
        """Get transactions by category id and user uuid"""
        pass

    @abstractmethod
    async def get_by_type(
        self,
        user_id: int,
        transaction_type: TransactionType,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Transaction]:
        """Get transactions by transaction type and user uuid"""
        pass

    @abstractmethod
    async def update(self, transaction: Transaction) -> Optional[Transaction]:
        """Update transaction"""
        pass

    @abstractmethod
    async def get_by_uuid_and_user_id(
        self, uuid: str, user_id: int
    ) -> Optional[Transaction]:
        """Get transaction by UUID and user ID for ownership validation"""
        pass

    # @abstractmethod
    # async def delete(self, transaction: Transaction):
    #     """Delete transaction"""
    #     pass

    @abstractmethod
    async def get_total_by_type(
        self,
        user_id: int,
        transaction_type: TransactionType,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        account_id: Optional[int] = None,
    ) -> float:
        """Get total amount by transaction type and user uuid"""
        pass

    @abstractmethod
    async def get_monthly_summary(
        self, user_id: int, year: int, month: int, account_id: Optional[int] = None
    ) -> dict:
        """Get monthly summary by user uuid"""
        pass

    @abstractmethod
    async def count_by_user(self, user_id: int) -> int:
        """Count transactions by user uuid"""
        pass

    @abstractmethod
    async def get_activity_by_account_id(
        self, account_id: int, limit: int = 5
    ) -> List[Tuple[Transaction, Optional[str]]]:
        """Get transactions by account id and user uuid
        The limit is a default value of 5
        """
        pass

    @abstractmethod
    async def get_filtered(
        self,
        user_id: int,
        account_uuid: Optional[str] = None,
        transaction_type: Optional[TransactionType] = None,
        category_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Tuple[Transaction, str, AccountType, Optional[str], Optional[str]]]:
        pass
