from datetime import datetime
from typing import cast

from sqlalchemy import delete, or_, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.auth.password_reset_token import PasswordResetToken
from domain.repositories.auth.password_reset_token_repository import (
    PasswordResetTokenRepository,
)
from infrastructure.database.models.password_reset_token import (
    PasswordResetTokenModel,
)
from shared.utils.time import as_utc


class SQLAlchemyPasswordResetTokenRepository(PasswordResetTokenRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add(self, token: PasswordResetToken) -> None:
        self.db.add(
            PasswordResetTokenModel(
                token_hash=token.token_hash,
                user_id=token.user_id,
                created_at=token.created_at,
                expires_at=token.expires_at,
                used_at=token.used_at,
            )
        )
        await self.db.flush()

    async def get(self, token_hash: str) -> PasswordResetToken | None:
        model = await self.db.get(
            PasswordResetTokenModel, token_hash, populate_existing=True
        )
        if model is None:
            return None
        return PasswordResetToken(
            token_hash=model.token_hash,
            user_id=model.user_id,
            created_at=as_utc(model.created_at),
            expires_at=as_utc(model.expires_at),
            used_at=as_utc(model.used_at) if model.used_at else None,
        )

    async def consume(self, token_hash: str, now: datetime) -> bool:
        # UPDATE condicional: de dos canjes simultáneos solo uno cambia la fila.
        result = cast(
            CursorResult,
            await self.db.execute(
                update(PasswordResetTokenModel)
                .where(
                    PasswordResetTokenModel.token_hash == token_hash,
                    PasswordResetTokenModel.used_at.is_(None),
                    PasswordResetTokenModel.expires_at > now,
                )
                .values(used_at=now)
                .execution_options(synchronize_session=False)
            ),
        )
        return (result.rowcount or 0) == 1

    async def invalidate_for_user(self, user_id: int, now: datetime) -> int:
        result = cast(
            CursorResult,
            await self.db.execute(
                update(PasswordResetTokenModel)
                .where(
                    PasswordResetTokenModel.user_id == user_id,
                    PasswordResetTokenModel.used_at.is_(None),
                )
                .values(used_at=now)
                .execution_options(synchronize_session=False)
            ),
        )
        return result.rowcount or 0

    async def purge(self, *, expired_before: datetime, used_before: datetime) -> int:
        result = cast(
            CursorResult,
            await self.db.execute(
                delete(PasswordResetTokenModel).where(
                    or_(
                        PasswordResetTokenModel.expires_at < expired_before,
                        PasswordResetTokenModel.used_at < used_before,
                    )
                )
            ),
        )
        return result.rowcount or 0
