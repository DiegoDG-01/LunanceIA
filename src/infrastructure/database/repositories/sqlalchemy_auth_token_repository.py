from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from domain.repositories.auth_token_repository import AuthTokenRepository
from infrastructure.database.models.refresh_token import RefreshTokenModel


class SQLAlchemyAuthTokenRepository(AuthTokenRepository):
    def __init__(self, db: Session):
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
            self.db.flush()

            return True
        except Exception:
            return False

    async def get_refresh_token(
        self, user_id: int, refresh_hash_token: str
    ) -> Optional[RefreshTokenModel]:
        try:
            token = (
                self.db.query(RefreshTokenModel)
                .filter(
                    and_(
                        RefreshTokenModel.user_id == user_id,
                        RefreshTokenModel.token_hash == refresh_hash_token,
                        RefreshTokenModel.is_revoked.is_(False),
                        RefreshTokenModel.expired_at > datetime.now(),
                    )
                )
                .first()
            )

            return token if token is not None else None
        except Exception:
            return None

    async def revoke_refresh_token(self, user_id: int, refresh_hash_token: str) -> bool:
        try:
            result = (
                self.db.query(RefreshTokenModel)
                .filter(
                    and_(
                        RefreshTokenModel.user_id == user_id,
                        RefreshTokenModel.token_hash == refresh_hash_token,
                    )
                )
                .update({"is_revoked": True})
            )

            self.db.flush()
            return result > 0
        except Exception:
            return False

    async def revoke_all_refresh_tokens_for_user(self, user_id: int) -> bool:
        try:
            result = (
                self.db.query(RefreshTokenModel)
                .filter(RefreshTokenModel.user_id == user_id)
                .update({"is_revoked": 1})
            )

            self.db.flush()
            return result > 0
        except Exception:
            return False

    async def cleanup_expired_tokens(self) -> bool:
        try:
            self.db.query(RefreshTokenModel).filter(
                RefreshTokenModel.expired_at < datetime.now(),
                RefreshTokenModel.is_revoked.is_(True),
            ).delete()

            self.db.flush()
            return True
        except Exception:
            return False

    async def is_token_valid(self, user_id: int, refresh_hash_token: str) -> bool:
        try:
            token = (
                self.db.query(RefreshTokenModel)
                .filter(
                    and_(
                        RefreshTokenModel.user_id == user_id,
                        RefreshTokenModel.token_hash == refresh_hash_token,
                        RefreshTokenModel.is_revoked.is_(False),
                        RefreshTokenModel.expired_at > datetime.now(),
                    )
                )
                .first()
            )

            return token is not None
        except Exception:
            return False

    async def revoke_token(self, user_id: int, refresh_hash_token: str) -> bool:
        return await self.revoke_refresh_token(user_id, refresh_hash_token)

    async def save_token(
        self, user_id: int, refresh_hash_token: str, expires_at: datetime
    ) -> bool:
        return await self.save_refresh_token(user_id, refresh_hash_token, expires_at)
