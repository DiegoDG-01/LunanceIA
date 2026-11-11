from datetime import datetime
from typing import cast

from sqlalchemy import delete, exists, or_, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.auth.session import Platform, RevocationReason, UserSession
from domain.repositories.auth.session_repository import SessionRepository
from infrastructure.database.models.refresh_token import RefreshTokenModel
from infrastructure.database.models.user_session import UserSessionModel
from shared.utils.time import as_utc


class SQLAlchemySessionRepository(SessionRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _model_to_entity(model: UserSessionModel) -> UserSession:
        return UserSession(
            id=model.id,
            uuid=model.uuid,
            user_id=model.user_id,
            device_id=model.device_id,
            platform=Platform(model.platform),
            device_name=model.device_name,
            client=model.client,
            user_agent=model.user_agent,
            created_ip=model.created_ip,
            last_ip=model.last_ip,
            created_at=as_utc(model.created_at),
            last_seen_at=as_utc(model.last_seen_at),
            idle_expires_at=as_utc(model.idle_expires_at),
            absolute_expires_at=as_utc(model.absolute_expires_at),
            revoked_at=as_utc(model.revoked_at) if model.revoked_at else None,
            revoked_reason=(
                RevocationReason(model.revoked_reason) if model.revoked_reason else None
            ),
        )

    @staticmethod
    def _apply(model: UserSessionModel, session: UserSession) -> None:
        model.uuid = session.uuid
        model.user_id = session.user_id
        model.device_id = session.device_id
        model.platform = session.platform
        model.device_name = session.device_name
        model.client = session.client
        model.user_agent = session.user_agent
        model.created_ip = session.created_ip
        model.last_ip = session.last_ip
        model.created_at = session.created_at
        model.last_seen_at = session.last_seen_at
        model.idle_expires_at = session.idle_expires_at
        model.absolute_expires_at = session.absolute_expires_at
        model.revoked_at = session.revoked_at
        model.revoked_reason = (
            session.revoked_reason.value if session.revoked_reason else None
        )

    async def add(self, session: UserSession) -> UserSession:
        model = UserSessionModel()
        self._apply(model, session)
        self.db.add(model)
        await self.db.flush()
        session.id = model.id
        return session

    async def get(
        self, session_id: int, *, for_update: bool = False
    ) -> UserSession | None:
        stmt = select(UserSessionModel).where(UserSessionModel.id == session_id)
        if for_update:
            stmt = stmt.with_for_update()
        stmt = stmt.execution_options(populate_existing=True)
        model = (await self.db.execute(stmt)).scalar_one_or_none()
        return self._model_to_entity(model) if model else None

    async def get_by_uuid(
        self, session_uuid: str, *, for_update: bool = False
    ) -> UserSession | None:
        stmt = select(UserSessionModel).where(UserSessionModel.uuid == session_uuid)
        if for_update:
            stmt = stmt.with_for_update()
        stmt = stmt.execution_options(populate_existing=True)
        model = (await self.db.execute(stmt)).scalar_one_or_none()
        return self._model_to_entity(model) if model else None

    async def save(self, session: UserSession) -> None:
        model = await self.db.get(UserSessionModel, session.id)
        if model is None:
            return
        self._apply(model, session)
        await self.db.flush()

    async def list_active(self, user_id: int, now: datetime) -> list[UserSession]:
        stmt = (
            select(UserSessionModel)
            .where(
                UserSessionModel.user_id == user_id,
                UserSessionModel.revoked_at.is_(None),
                UserSessionModel.idle_expires_at > now,
                UserSessionModel.absolute_expires_at > now,
            )
            .order_by(UserSessionModel.last_seen_at.desc(), UserSessionModel.id.desc())
        )
        models = (await self.db.execute(stmt)).scalars().all()
        return [self._model_to_entity(model) for model in models]

    async def revoke_active(
        self,
        user_id: int,
        now: datetime,
        reason: RevocationReason,
        *,
        device_id: str | None = None,
        except_uuid: str | None = None,
    ) -> list[UserSession]:
        # MySQL no tiene UPDATE … RETURNING: se bloquean las filas, se cambian y se devuelven.
        stmt = (
            select(UserSessionModel)
            .where(
                UserSessionModel.user_id == user_id,
                UserSessionModel.revoked_at.is_(None),
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if device_id is not None:
            stmt = stmt.where(UserSessionModel.device_id == device_id)
        if except_uuid is not None:
            stmt = stmt.where(UserSessionModel.uuid != except_uuid)
        models = (await self.db.execute(stmt)).scalars().all()
        for model in models:
            model.revoked_at = now
            model.revoked_reason = reason.value
        await self.db.flush()
        return [self._model_to_entity(model) for model in models]

    async def has_device(self, user_id: int, device_id: str) -> bool:
        stmt = select(
            exists().where(
                UserSessionModel.user_id == user_id,
                UserSessionModel.device_id == device_id,
            )
        )
        return bool((await self.db.execute(stmt)).scalar())

    async def purge(self, *, expired_before: datetime, revoked_before: datetime) -> int:
        purgeable = or_(
            UserSessionModel.revoked_at < revoked_before,
            UserSessionModel.idle_expires_at < expired_before,
            UserSessionModel.absolute_expires_at < expired_before,
        )
        # La FK ya borra en cascada; se hace explícito para no depender de ella (SQLite).
        await self.db.execute(
            delete(RefreshTokenModel).where(
                RefreshTokenModel.session_id.in_(
                    select(UserSessionModel.id).where(purgeable)
                )
            )
        )
        result = cast(
            CursorResult,
            await self.db.execute(delete(UserSessionModel).where(purgeable)),
        )
        return result.rowcount or 0
