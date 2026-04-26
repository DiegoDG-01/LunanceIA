from abc import ABC, abstractmethod
from typing import List

from domain.entities.notification import Notification


class NotificationRepository(ABC):

    @abstractmethod
    async def create(self, notification: Notification) -> Notification:
        """Create Notification"""
        pass

    @abstractmethod
    async def get_by_user_id(self, user_id: int) -> List[Notification]:
        """Get Notification by id"""
        pass

    @abstractmethod
    async def delete_by_user_id(self, user_id: int) -> None:
        """Delete all notifications for a user"""
        pass