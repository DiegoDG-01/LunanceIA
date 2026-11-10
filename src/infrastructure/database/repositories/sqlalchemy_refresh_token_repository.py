from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.auth.refresh_token import RefreshToken
from domain.repositories.auth.refresh_token_repository import RefreshTokenRepository
from infrastructure.database.models.refresh_token import RefreshTokenModel
from shared.utils.time import as_utc


class SQLAlchemyRefreshTokenRepository(RefreshTokenRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add(self, token: RefreshToken) -> None:
        self.db.add(
            RefreshTokenModel(
                token_hash=token.token_hash,
                session_id=token.session_id,
                created_at=token.created_at,
                rotated_at=token.rotated_at,
            )
        )
        await self.db.flush()

    async def get(
        self, token_hash: str, *, for_update: bool = False
    ) -> RefreshToken | None:
        stmt = select(RefreshTokenModel).where(
            RefreshTokenModel.token_hash == token_hash
        )
        if for_update:
            # Una lectura con bloqueo ve la última versión confirmada, no la foto de la
            # transacción (REPEATABLE READ): así se ve si otro refresh acaba de rotarlo.
            stmt = stmt.with_for_update()
        stmt = stmt.execution_options(populate_existing=True)
        model = (await self.db.execute(stmt)).scalar_one_or_none()
        if model is None:
            return None
        return RefreshToken(
            token_hash=model.token_hash,
            session_id=model.session_id,
            created_at=as_utc(model.created_at),
            rotated_at=as_utc(model.rotated_at) if model.rotated_at else None,
        )

    async def rotate_active(self, session_id: int, now: datetime) -> None:
        await self.db.execute(
            update(RefreshTokenModel)
            .where(
                RefreshTokenModel.session_id == session_id,
                RefreshTokenModel.rotated_at.is_(None),
            )
            .values(rotated_at=now)
            .execution_options(synchronize_session="fetch")
        )
