import logging
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.api_key import APIKey
from domain.repositories.api_key_repository import APIKeyRepository
from infrastructure.database.models.api_key import APIKeyModel

logger = logging.getLogger(__name__)


class SQLAlchemyAPIKeyRepository(APIKeyRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _model_to_entity(model: APIKeyModel) -> APIKey:
        return APIKey(
            id=model.id,
            uuid=model.uuid,
            user_id=model.user_id,
            name=model.name,
            scopes=model.scopes,
            key_hash=model.key_hash,
            key_prefix=model.key_prefix,
            is_active=model.is_active,
            expires_at=model.expires_at,
            last_used_at=model.last_used_at,
            created_at=model.created_at,
        )

    @staticmethod
    def _entity_to_model(entity: APIKey) -> APIKeyModel:
        return APIKeyModel(
            id=entity.id,
            uuid=entity.uuid,
            user_id=entity.user_id,
            name=entity.name,
            scopes=entity.scopes,
            key_hash=entity.key_hash,
            key_prefix=entity.key_prefix,
            is_active=entity.is_active,
            expires_at=entity.expires_at,
        )

    async def create(self, api_key: APIKey) -> APIKey:
        model = self._entity_to_model(api_key)
        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)
        return self._model_to_entity(model)

    async def get_by_hash(self, key_hash: str) -> APIKey | None:
        stmt = select(APIKeyModel).where(APIKeyModel.key_hash == key_hash)
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        return self._model_to_entity(model) if model else None

    async def list_by_user(self, user_id: int) -> list[APIKey]:
        stmt = select(APIKeyModel).where(APIKeyModel.user_id == user_id)
        result = await self.db.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_entity(model) for model in models]

    async def revoke(self, uuid: str, user_id: int) -> bool:
        stmt = select(APIKeyModel).where(
            APIKeyModel.uuid == uuid, APIKeyModel.user_id == user_id
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            model.is_active = False
            await self.db.flush()
            return True
        return False

    async def delete(self, uuid: str, user_id: int) -> bool:
        stmt = select(APIKeyModel).where(
            APIKeyModel.uuid == uuid, APIKeyModel.user_id == user_id
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            await self.db.delete(model)
            await self.db.flush()
            return True
        return False

    async def touch_last_used(self, api_key_id: int) -> None:
        stmt = (
            update(APIKeyModel)
            .where(APIKeyModel.id == api_key_id)
            .values(last_used_at=datetime.now(UTC))
        )
        await self.db.execute(stmt)
