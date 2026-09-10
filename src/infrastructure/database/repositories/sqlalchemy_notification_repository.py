from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.notification import Notification
from domain.objects.enums import NotificationType
from domain.repositories.notification_repository import NotificationRepository
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
            created_at=entity.created_at,
        )

    async def create(self, notification: Notification) -> Notification:
        model = self._entity_to_model(notification)
        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)
        return self._model_to_entity(model)

    async def get_by_user_id(self, user_id: int) -> list[Notification]:
        stmt = select(NotificationModel).where(NotificationModel.user_id == user_id)
        result = await self.db.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_entity(model) for model in models]

    async def delete_by_user_id(self, user_id: int) -> None:
        stmt = delete(NotificationModel).where(NotificationModel.user_id == user_id)
        await self.db.execute(stmt)
        await self.db.flush()
