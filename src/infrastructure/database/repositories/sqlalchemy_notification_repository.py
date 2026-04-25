from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from domain.entities.notification import Notification
from domain.repositories.notification_repository import NotificationRepository
from domain.objects.enums import NotificationType

from infrastructure.database.models.notifications import NotificationModel


class SQLAlchemyNotificationRepository(NotificationRepository):

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _model_to_entity(model: NotificationModel) -> Notification:
        return Notification(
            id=model.id,
            user_id=model.user_id,
            title=model.title,
            message=model.message,
            type=NotificationType(model.type),
            is_read=model.is_read,
            created_at=model.created_at,
        )

    @staticmethod
    def _entity_to_model(entity: Notification) -> NotificationModel:
        return NotificationModel(
            id=entity.id,
            user_id=entity.user_id,
            title=entity.title,
            message=entity.message,
            type=entity.type.value,
            is_read=entity.is_read,
            created_at=entity.created_at
        )

    async def create(self, notification: Notification) -> Notification:
        model = self._entity_to_model(notification)
        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)
        return self._model_to_entity(model)

    async def delete(self, notification: int) -> bool:
        stmt = select(NotificationModel).where(NotificationModel.id == notification)
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return False

        await self.db.delete(model)
        await self.db.flush()
        return True

    async def get_by_user_id(self, user_id: int) -> List[Notification]:
        stmt = select(NotificationModel).where(NotificationModel.user_id == user_id)
        result = await self.db.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_entity(model) for model in models]