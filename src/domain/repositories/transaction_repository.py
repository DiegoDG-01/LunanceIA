from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import date, datetime

from domain.entities.transaction import Transaction
from domain.objects.enums import TransactionType


class TransactionRepository(ABC):
    """
    Interface for transaction repository
    """

    @abstractmethod
    def create(self, transaction: Transaction):
        """Create transaction"""
        pass

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[Transaction]:
        """Get transaction by id"""
        pass

    @abstractmethod
    def get_by_id_and_user(self, id: int, user_uuid: str) -> Optional[Transaction]:
        """Get transaction by id and user uuid"""
        pass

    @abstractmethod
    def get_by_account(
            self,
            account_id: int,
            user_uuid: str,
            limit: int = 100,
            offset: int = 0
    ) -> List[Transaction]:
        """Get transactions by account id and user uuid"""
        pass

    @abstractmethod
    def get_by_date_range(
            self,
            user_uuid: str,
            start_date: date,
            end_date: date,
            account_id: Optional[int] = None,
            transaction_type: Optional[TransactionType] = None,
    ) -> List[Transaction]:
        """Get transactions by date range and user uuid"""
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
            offset: int = 0
    ) -> List[Transaction]:
        """Get transactions by transaction type and user uuid"""
        pass

    @abstractmethod
    def update(self, transaction: Transaction):
        """Update transaction"""
        pass

    @abstractmethod
    def delete(self, transaction: Transaction):
        """Delete transaction"""
        pass

    @abstractmethod
    def get_total_by_type(
            self, user_uuid: str,
            transaction_type: TransactionType,
            start_date: date,
            end_date: date,
            account_id: Optional[int] = None
    ) -> float:
        """Get total amount by transaction type and user uuid"""
        pass

    @abstractmethod
    def get_monthly_summary(
            self,
            user_uuid: str,
            year: int,
            month: int,
            account_id: Optional[int] = None
    ) -> List[dict]:
        """Get monthly summary by user uuid"""
        pass


    @abstractmethod
    def count_by_user(self, user_uuid: str) -> int:
        """Count transactions by user uuid"""
        pass
