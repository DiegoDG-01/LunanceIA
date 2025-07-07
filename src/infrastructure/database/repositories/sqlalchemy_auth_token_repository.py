from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, update

from domain.repositories.auth_token_repository import AuthTokenRepository
from infrastructure.database.models.refresh_token import RefreshTokenModel
from infrastructure.database.connection import get_db


class SQLAlchemyAuthTokenRepository(AuthTokenRepository):
    def __init__(self, db: Session = next(get_db())):
        self.db = db

    async def save_refresh_token(self, user_uuid: str, refresh_hash_token: str, expires_at: datetime) -> bool:
        try:
            self.revoke_all_refresh_tokens_for_user(user_uuid)

            new_refresh_token = RefreshTokenModel(
                user_uuid=user_uuid,
                token_hash=refresh_hash_token,
                is_revoked=False,
                expired_at=expires_at
            )

            self.db.add(new_refresh_token)
            self.db.commit()

            return True
        except Exception as e:
            self.db.rollback()
            return False


    async def get_refresh_token(self, user_uuid: str, refresh_hash_token: str) -> Optional[RefreshTokenModel]:
        try:
            token = self.db.query(RefreshTokenModel).filter(
                and_(
                    RefreshTokenModel.user_uuid == user_uuid,
                    RefreshTokenModel.token_hash == refresh_hash_token,
                    RefreshTokenModel.is_revoked == False,
                    RefreshTokenModel.expired_at > datetime.now()
                )
            ).first()

            if token:
                return token

            return None
        except Exception as e:
            return None


    async def revoke_refresh_token(self, user_uuid: str, refresh_hash_token: str) -> bool:
        try:
            result = self.db.query(RefreshTokenModel).filter(
                and_(
                    RefreshTokenModel.user_uuid == user_uuid,
                    RefreshTokenModel.token_hash == refresh_hash_token,
                )
            ).update({
                "is_revoked": True
            })

            self.db.commit()
            return result > 0
        except Exception as e:
            self.db.rollback()
            return False


    async def revoke_all_refresh_tokens_for_user(self, user_uuid: str) -> bool:
        try:
            result = self.db.query(RefreshTokenModel).filter(
                RefreshTokenModel.user_uuid == user_uuid
            ).update({
                "is_revoked": True
            })

            self.db.commit()
            return result > 0
        except Exception as e:
            self.db.rollback()
            return False


    async def cleanup_expired_tokens(self) -> bool:
        try:
            self.db.query(RefreshTokenModel).filter(
                RefreshTokenModel.expired_at < datetime.now(),
                RefreshTokenModel.is_revoked == True
            ).delete()

            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            return False

    async def is_token_valid(self, user_id: int, hash_refresh_token: str) -> bool:
        try:
            token = self.db.query(RefreshTokenModel).filter(
                and_(
                    RefreshTokenModel.user_uuid == str(user_id),
                    RefreshTokenModel.token_hash == hash_refresh_token,
                    RefreshTokenModel.is_revoked == False,
                    RefreshTokenModel.expired_at > datetime.now()
                )
            ).first()
            
            return token is not None
        except Exception as e:
            return False

    async def revoke_token(self, user_id: int, refresh_hash_token: str) -> bool:
        return await self.revoke_refresh_token(str(user_id), refresh_hash_token)

    async def save_token(self, user_id: int, refresh_hash_token: str, expires_at: datetime) -> bool:
        return await self.save_refresh_token(str(user_id), refresh_hash_token, expires_at)

