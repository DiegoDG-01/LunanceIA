from abc import ABC, abstractmethod

from domain.entities.notification import Notification


class NotificationRepository(ABC):
    @abstractmethod
    async def create(self, notification: Notification) -> Notification:
        """Create Notification"""

    @abstractmethod
    async def get_by_user_id(self, user_id: int) -> list[Notification]:
        """Get Notification by id"""

    @abstractmethod
    async def delete_by_user_id(self, user_id: int) -> None:
        """Delete all notifications for a user"""
