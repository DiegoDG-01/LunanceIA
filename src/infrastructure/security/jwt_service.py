from datetime import datetime, timedelta, timezone
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
import hashlib
import logging

from sqlalchemy.exc import SQLAlchemyError

from infrastructure.config.settings import settings
from domain.repositories.auth_token_repository import AuthTokenRepository
from domain.repositories.user_repository import UserRepository
from shared.exceptions.application import JWTValidationError, RepositoryError

logger = logging.getLogger(__name__)


class JWTService:
    def __init__(
        self,
        user_repository: UserRepository,
        auth_token_repository: AuthTokenRepository,
    ):
        self.user_repository = user_repository
        self.auth_token_repository = auth_token_repository
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def check_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)

    def create_access_token(self, user_uuid: str, expires_in: Optional[int] = None):
        now = datetime.now(timezone.utc)
        if expires_in:
            expire = now + timedelta(minutes=expires_in)
        else:
            expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode = {"exp": expire, "iat": int(now.timestamp()), "sub": user_uuid}

        encoded_jwt = jwt.encode(
            to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )

        return encoded_jwt

    def create_refresh_token(self, user_uuid: str, expires_in: Optional[int] = None):
        if expires_in:
            expire = datetime.now(timezone.utc) + timedelta(days=expires_in)
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            )
        to_encode = {"exp": expire, "sub": user_uuid, "type": "refresh"}
        encoded_jwt = jwt.encode(
            to_encode, settings.SECRET_KEY_REFRESH, algorithm=settings.ALGORITHM
        )
        return encoded_jwt

    def verify_access_token(self, token: str):
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=settings.ALGORITHM
            )
            user_uuid = payload.get("sub")
            if user_uuid is None:
                return None
            return user_uuid
        except JWTError:
            return None

    async def verify_refresh_token(self, token: str):
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY_REFRESH, algorithms=settings.ALGORITHM
            )
            user_uuid = payload.get("sub")
            token_type = payload.get("type")

            if user_uuid is None or token_type != "refresh":
                return None

            user = await self.user_repository.get_by_uuid(user_uuid)
            if user is None:
                return None

            # Validate token against database using repository
            token_hash = self.hash_refresh_token(token)
            is_valid = await self.auth_token_repository.get_refresh_token(
                user_id=user.id, refresh_hash_token=token_hash
            )

            return user_uuid if is_valid is not None else None
        except JWTError as e:
            raise JWTValidationError(str(e))
        except SQLAlchemyError as e:
            logger.error(f"Database error verifying refresh token: {e}")
            raise RepositoryError("verify", "RefreshToken", str(e))

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        return self.pwd_context.hash(password)

    async def revoke_refresh_token(self, token: str) -> bool:
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY_REFRESH, algorithms=settings.ALGORITHM
            )
            user_uuid = payload.get("sub")
            token_type = payload.get("type")

            if user_uuid is None or token_type != "refresh":
                return False

            user = await self.user_repository.get_by_uuid(user_uuid)
            if user is None:
                return False
            
            token_hash = self.hash_refresh_token(token)
            return await self.auth_token_repository.revoke_refresh_token(user.id, token_hash)
        except JWTError:
            return False
        except SQLAlchemyError as e:
            logger.error(f"Database error to revoke refresh token: {e}")
            return False

    async def save_refresh_token(
        self, user_id: int, token: str, expires_at: datetime
    ) -> bool:
        token_hash = self.hash_refresh_token(token)

        try:
            return await self.auth_token_repository.save_refresh_token(
                user_id, token_hash, expires_at
            )
        except SQLAlchemyError as e:
            logger.error(f"Database error to save refresh token: {e}")
            raise RepositoryError("save", "RefreshToken", str(e))

    @staticmethod
    def hash_refresh_token(token: str):
        return hashlib.sha256(token.encode()).hexdigest()
