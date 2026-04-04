import logging
from typing import Optional, cast
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, delete
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import SQLAlchemyError

from domain.repositories.auth_token_repository import AuthTokenRepository
from domain.entities.refresh_token import RefreshToken
from infrastructure.database.models.refresh_token import RefreshTokenModel
from shared.exceptions.application import RepositoryError

logger = logging.getLogger(__name__)


class SQLAlchemyAuthTokenRepository(AuthTokenRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_refresh_token(
        self, user_id: int, refresh_hash_token: str, expires_at: datetime
    ) -> bool:
        try:
            await self.revoke_all_refresh_tokens_for_user(user_id)

            new_refresh_token = RefreshTokenModel(
                user_id=user_id,
                token_hash=refresh_hash_token,
                is_revoked=False,
                expired_at=expires_at,
            )

            self.db.add(new_refresh_token)
            await self.db.flush()

            return True
        except SQLAlchemyError as e:
            logger.error(e)
            raise RepositoryError(
                operation="save",
                entity="RefreshToken",
                details=str(e),
            ) from e

    async def get_refresh_token(
        self, user_id: int, refresh_hash_token: str
    ) -> Optional[RefreshToken]:
        try:
            stmt = select(RefreshTokenModel).where(
                and_(
                    RefreshTokenModel.user_id == user_id,
                    RefreshTokenModel.token_hash == refresh_hash_token,
                    RefreshTokenModel.is_revoked.is_(False),
                    RefreshTokenModel.expired_at > datetime.now(),
                )
            )
            result = await self.db.execute(stmt)
            token = result.scalars().first()

            if token is None:
                return None
            return RefreshToken(
                id=token.id,
                user_id=token.user_id,
                token_hash=token.token_hash,
                is_revoked=token.is_revoked,
                expired_at=token.expired_at,
                created_at=token.created_at,
            )
        except SQLAlchemyError as e:
            logger.error(e)
            raise RepositoryError(
                operation="get",
                entity="RefreshToken",
                details=str(e),
            ) from e

    async def revoke_refresh_token(self, user_id: int, refresh_hash_token: str) -> bool:
        try:
            stmt = (
                update(RefreshTokenModel)
                .where(
                    and_(
                        RefreshTokenModel.user_id == user_id,
                        RefreshTokenModel.token_hash == refresh_hash_token,
                    )
                )
                .values(is_revoked=True)
            )

            result = cast(CursorResult, await self.db.execute(stmt))

            await self.db.flush()
            return result.rowcount > 0
        except SQLAlchemyError as e:
            logger.error(e)
            raise RepositoryError(
                operation="revoke",
                entity="RefreshToken",
                details=str(e),
            ) from e

    async def revoke_all_refresh_tokens_for_user(self, user_id: int) -> bool:
        try:
            stmt = (
                update(RefreshTokenModel)
                .where(
                    and_(
                        RefreshTokenModel.user_id == user_id,
                    )
                )
                .values(is_revoked=True)
            )

            result = cast(CursorResult, await self.db.execute(stmt))

            await self.db.flush()
            return result.rowcount > 0
        except SQLAlchemyError as e:
            logger.error(e)
            raise RepositoryError(
                operation="revoke_all",
                entity="RefreshToken",
                details=str(e),
            ) from e

    async def cleanup_expired_tokens(self) -> bool:
        try:
            stmt = delete(RefreshTokenModel).where(
                RefreshTokenModel.expired_at < datetime.now(),
                RefreshTokenModel.is_revoked.is_(True),
            )
            await self.db.execute(stmt)
            return True
        except SQLAlchemyError as e:
            logger.error(e)
            raise RepositoryError(
                operation="cleanup",
                entity="RefreshToken",
                details=str(e),
            ) from e
