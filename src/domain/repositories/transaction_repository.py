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
    def create(self, transaction: Transaction) -> Transaction:
        """Create transaction"""
        pass

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[Transaction]:
        """Get transaction by id"""
        pass

    @abstractmethod
    def delete_by_uuid(self, uuid: str, user_id: int) -> bool:
        """
        Delete transaction by UUID with ownership validation.

        Returns:
            bool: True if deleted, False if not found or access denied
        """

    pass

    @abstractmethod
    def get_by_id_and_user_uuid(self, id: int, user_id: int) -> Optional[Transaction]:
        """Get transaction by id and user uuid"""
        pass

    @abstractmethod
    def get_by_account(
        self, account_uuid: str, user_id: int, limit: int = 100, offset: int = 0
    ) -> List[Transaction]:
        """Get transactions by account id and user uuid"""
        pass

    @abstractmethod
    def get_by_date_range(
        self,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        account_uuid: Optional[str] = None,
        transaction_type: Optional[TransactionType] = None,
    ) -> List[Tuple[Transaction, str, AccountType, Optional[str]]]:
        """Get transactions by date range and user uuid"""
        pass

    @abstractmethod
    def get_by_uuid_with_account_details(
        self, uuid: str, user_id: int
    ) -> Optional[Tuple[Transaction, str, AccountType, Optional[str]]]:
        """Get transaction by uuid and user id with account details (name, type, bank)"""
        pass

    @abstractmethod
    def get_by_user(
        self, user_id: int, limit: int = 100, offset: int = 0
    ) -> List[Tuple[Transaction, str, AccountType, Optional[str]]]:
        """Get transactions by user uuid"""
        pass

    @abstractmethod
    def get_by_category(
        self,
        user_uuid: str,
        category_id: int,
        start_date: date,
        end_date: date,
    ) -> List[Transaction]:
        """Get transactions by category id and user uuid"""
        pass

    @abstractmethod
    def get_by_type(
        self,
        user_uuid: str,
        transaction_type: TransactionType,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Transaction]:
        """Get transactions by transaction type and user uuid"""
        pass

    @abstractmethod
    def update(
        self, transaction_uuid: str, user_id: int, updates: dict
    ) -> Optional[Transaction]:
        """Update transaction"""
        pass

    @abstractmethod
    def get_by_uuid_and_user_id(self, uuid: str, user_id: int) -> Optional[Transaction]:
        """Get transaction by UUID and user ID for ownership validation"""
        pass

    # @abstractmethod
    # def delete(self, transaction: Transaction):
    #     """Delete transaction"""
    #     pass

    @abstractmethod
    def get_total_by_type(
        self,
        user_uuid: str,
        transaction_type: TransactionType,
        start_date: date,
        end_date: date,
        account_id: Optional[int] = None,
    ) -> float:
        """Get total amount by transaction type and user uuid"""
        pass

    @abstractmethod
    def get_monthly_summary(
        self, user_uuid: str, year: int, month: int, account_id: Optional[int] = None
    ) -> List[dict]:
        """Get monthly summary by user uuid"""
        pass

    @abstractmethod
    def count_by_user(self, user_uuid: str) -> int:
        """Count transactions by user uuid"""
        pass
