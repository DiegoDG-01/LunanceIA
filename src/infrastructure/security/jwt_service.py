import hashlib
import logging
from datetime import UTC, datetime, timedelta
from typing import cast

import bcrypt
from jose import JWTError, jwt
from sqlalchemy.exc import SQLAlchemyError

from application.interfaces.auth_service import AuthTokenServiceInterface
from domain.repositories.auth_token_repository import AuthTokenRepository
from domain.repositories.user_repository import UserRepository
from infrastructure.config.settings import settings
from shared.exceptions.application import JWTValidationError, RepositoryError

logger = logging.getLogger(__name__)


class JWTService(AuthTokenServiceInterface):
    def __init__(
        self,
        user_repository: UserRepository,
        auth_token_repository: AuthTokenRepository,
    ):
        self.user_repository = user_repository
        self.auth_token_repository = auth_token_repository

    def check_password(self, plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

    def create_access_token(self, user_uuid: str, expires_in: int | None = None):
        now = datetime.now(UTC)
        if expires_in:
            expire = now + timedelta(minutes=expires_in)
        else:
            expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode = {
            "exp": expire,
            "iat": int(now.timestamp()),
            "sub": user_uuid,
            "iss": "lunance",
        }

        encoded_jwt = jwt.encode(
            to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )

        return encoded_jwt

    def create_refresh_token(self, user_uuid: str, expires_in: int | None = None):
        if expires_in:
            expire = datetime.now(UTC) + timedelta(days=expires_in)
        else:
            expire = datetime.now(UTC) + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            )
        to_encode = {"exp": expire, "sub": user_uuid, "type": "refresh"}
        encoded_jwt = jwt.encode(
            to_encode, settings.SECRET_KEY_REFRESH, algorithm=settings.ALGORITHM
        )
        return encoded_jwt

    async def verify_refresh_token(self, token: str):
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY_REFRESH, algorithms=[settings.ALGORITHM]
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
                user_id=cast(int, user.id), refresh_hash_token=token_hash
            )

            return user_uuid if is_valid is not None else None
        except JWTError as e:
            raise JWTValidationError(str(e))
        except SQLAlchemyError as e:
            logger.error(f"Database error verifying refresh token: {e}")
            raise RepositoryError("verify", "RefreshToken", str(e))

    def get_password_hash(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

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
