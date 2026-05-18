from dataclasses import dataclass
from typing import List

from domain.entities.notification import Notification
from domain.repositories.notification_repository import NotificationRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork


@dataclass
class GetAndClearNotificationsQuery:
    user_id: int


class GetAndClearNotificationsHandler:
    def __init__(
        self,
        notification_repository: NotificationRepository,
        uow: AbstractUnitOfWork,
    ):
        self.notification_repository = notification_repository
        self.uow = uow

    async def handle(self, query: GetAndClearNotificationsQuery) -> List[Notification]:
        notifications = await self.notification_repository.get_by_user_id(query.user_id)

        if notifications:
            async with self.uow:
                await self.notification_repository.delete_by_user_id(query.user_id)
                await self.uow.commit()

        return notifications
