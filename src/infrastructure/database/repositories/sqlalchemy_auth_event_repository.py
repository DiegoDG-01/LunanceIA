from datetime import datetime
from typing import cast

from sqlalchemy import delete
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.auth.auth_event import AuthEvent
from domain.repositories.auth.auth_event_repository import AuthEventRepository
from infrastructure.database.models.auth_event import AuthEventModel


class SQLAlchemyAuthEventRepository(AuthEventRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record(self, event: AuthEvent) -> None:
        self.db.add(
            AuthEventModel(
                user_id=event.user_id,
                session_id=event.session_id,
                action=event.action.value,
                ip=event.ip,
                user_agent=event.user_agent,
                details=event.details or None,
                created_at=event.created_at,
            )
        )
        await self.db.flush()

    async def purge(self, *, created_before: datetime) -> int:
        result = cast(
            CursorResult,
            await self.db.execute(
                delete(AuthEventModel).where(AuthEventModel.created_at < created_before)
            ),
        )
        return result.rowcount or 0
