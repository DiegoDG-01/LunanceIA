from abc import ABC, abstractmethod
from typing import Optional, List

from domain.entities.subscription import Subscription


class SubscriptionRepository(ABC):
    @abstractmethod
    def create(self, subscription: Subscription) -> Subscription:
        """Create subscription"""
        pass

    @abstractmethod
    def update(self, subscription: Subscription) -> Subscription:
        """Update subscription"""
        pass

    @abstractmethod
    def delete(self, uuid: str, user_id: int) -> bool:
        """
        Delete transaction by UUID with ownership validation.

        Returns:
            bool: True if deleted, False if not found or access denied
        """
        pass

    @abstractmethod
    def get_by_uuid_and_user_id(
        self, subscription_uuid: str, user_id: int
    ) -> Optional[Subscription]:
        """Get subscription by uuid"""
        pass

    @abstractmethod
    def get_by_account(
        self, account_uuid: str, user_id: int, limit: int = 100, offset: int = 0
    ) -> List[Subscription]:
        """Get subscriptions by account"""
        pass

    @abstractmethod
    def get_by_category(
        self,
        user_id: int,
        category_id: int,
    ) -> List[Subscription]:
        """Get subscriptions by category"""
        pass

    @abstractmethod
    def get_by_user(
        self, user_id: int, active_only: bool = False
    ) -> List[Subscription]:
        """Get all subscriptions for a user, optionally filter by active status"""
        pass

    @abstractmethod
    def get_active_subscriptions(self) -> List[Subscription]:
        """Get all active subscriptions"""
        pass
