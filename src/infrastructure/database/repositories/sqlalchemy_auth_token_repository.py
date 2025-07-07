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
        self, user_uuid: str, refresh_hash_token: str, expires_at: datetime
    ) -> bool:
        try:
            self.revoke_all_refresh_tokens_for_user(user_uuid)

            new_refresh_token = RefreshTokenModel(
                user_uuid=user_uuid,
                token_hash=refresh_hash_token,
                is_revoked=False,
                expired_at=expires_at,
            )

            self.db.add(new_refresh_token)
            self.db.commit()

            return True
        except Exception:
            self.db.rollback()
            return False

    async def get_refresh_token(
        self, user_uuid: str, refresh_hash_token: str
    ) -> Optional[RefreshTokenModel]:
        try:
            token = (
                self.db.query(RefreshTokenModel)
                .filter(
                    and_(
                        RefreshTokenModel.user_uuid == user_uuid,
                        RefreshTokenModel.token_hash == refresh_hash_token,
                        RefreshTokenModel.is_revoked.is_(False),
                        RefreshTokenModel.expired_at > datetime.now(),
                    )
                )
                .first()
            )

            if token:
                return token

            return None
        except Exception:
            return None

    async def revoke_refresh_token(
        self, user_uuid: str, refresh_hash_token: str
    ) -> bool:
        try:
            result = (
                self.db.query(RefreshTokenModel)
                .filter(
                    and_(
                        RefreshTokenModel.user_uuid == user_uuid,
                        RefreshTokenModel.token_hash == refresh_hash_token,
                    )
                )
                .update({"is_revoked": True})
            )

            self.db.commit()
            return result > 0
        except Exception:
            self.db.rollback()
            return False

    async def revoke_all_refresh_tokens_for_user(self, user_uuid: str) -> bool:
        try:
            result = (
                self.db.query(RefreshTokenModel)
                .filter(RefreshTokenModel.user_uuid == user_uuid)
                .update({"is_revoked": True})
            )

            self.db.commit()
            return result > 0
        except Exception:
            self.db.rollback()
            return False

    async def cleanup_expired_tokens(self) -> bool:
        try:
            self.db.query(RefreshTokenModel).filter(
                RefreshTokenModel.expired_at < datetime.now(),
                RefreshTokenModel.is_revoked.is_(True),
            ).delete()

            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False

    async def is_token_valid(self, user_uuid: str, hash_refresh_token: str) -> bool:
        try:
            token = (
                self.db.query(RefreshTokenModel)
                .filter(
                    and_(
                        RefreshTokenModel.user_uuid == user_uuid,
                        RefreshTokenModel.token_hash == hash_refresh_token,
                        RefreshTokenModel.is_revoked.is_(False),
                        RefreshTokenModel.expired_at > datetime.now(),
                    )
                )
                .first()
            )

            return token is not None
        except Exception:
            return False

    async def revoke_token(self, user_uuid: str, refresh_hash_token: str) -> bool:
        return await self.revoke_refresh_token(user_uuid, refresh_hash_token)

    async def save_token(
        self, user_uuid: str, refresh_hash_token: str, expires_at: datetime
    ) -> bool:
        return await self.save_refresh_token(user_uuid, refresh_hash_token, expires_at)
