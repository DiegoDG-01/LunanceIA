from fastapi import Depends

from application.notifications.queries.get_and_clear_notifications import (
    GetAndClearNotificationsHandler,
)
from domain.repositories.unit_of_work import AbstractUnitOfWork
from infrastructure.database.repositories.sqlalchemy_notification_repository import (
    SQLAlchemyNotificationRepository,
)
from presentation.dependencies.repositories import (
    get_notification_repository,
    get_unit_of_work_repository,
)


def get_notifications_handler(
    notification_repo: SQLAlchemyNotificationRepository = Depends(get_notification_repository),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> GetAndClearNotificationsHandler:
    return GetAndClearNotificationsHandler(notification_repo, uow)