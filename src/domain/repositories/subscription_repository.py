from abc import ABC, abstractmethod
from datetime import date

from domain.entities.subscription import Subscription


class SubscriptionRepository(ABC):
    @abstractmethod
    async def create(self, subscription: Subscription) -> Subscription:
        """Create subscription"""

    @abstractmethod
    async def update(self, subscription: Subscription) -> Subscription:
        """Update subscription"""

    @abstractmethod
    async def delete(self, uuid: str, user_id: int) -> bool:
        """
        Delete transaction by UUID with ownership validation.

        Returns:
            bool: True if deleted, False if not found or access denied
        """

    @abstractmethod
    async def get_by_uuid_and_user_id(
        self, subscription_uuid: str, user_id: int
    ) -> Subscription | None:
        """Get subscription by uuid"""

    @abstractmethod
    async def get_by_account(
        self, account_uuid: str, user_id: int, limit: int = 100, offset: int = 0
    ) -> list[Subscription]:
        """Get subscriptions by account"""

    @abstractmethod
    async def get_by_category(
        self,
        user_id: int,
        category_id: int,
    ) -> list[Subscription]:
        """Get subscriptions by category"""

    @abstractmethod
    async def get_by_user(
        self, user_id: int, active_only: bool = False
    ) -> list[Subscription]:
        """Get all subscriptions for a user, optionally filter by active status"""

    @abstractmethod
    # async def get_active_subscriptions(self) -> List[Subscription]:
    #     """Get all active subscriptions"""
    #     pass

    @abstractmethod
    async def switch_status(self, subscription: Subscription) -> Subscription:
        """Switch subscription status"""

    @abstractmethod
    async def get_due_subscriptions(self, as_of: date) -> list[Subscription]:
        pass
