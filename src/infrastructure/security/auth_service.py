from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from infrastructure.config.settings import settings
from infrastructure.database.models.refresh_token import RefreshTokenModel

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire, "type": "refresh"})

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_refresh_token(token: str, db: Session) -> Optional[RefreshTokenModel]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=settings.ALGORITHM)

        user_uuid = payload.get("sub")
        token_type = payload.get("type")

        if user_uuid is None or token_type != "refresh":
            return None

        refresh_token = db.query(RefreshTokenModel).filter(
            RefreshTokenModel.user_uuid == user_uuid,
            RefreshTokenModel.token_hash == hash_refresh_token(token),
            RefreshTokenModel.is_revoked is False,
            RefreshTokenModel.expired_at > datetime.now(timezone.utc)
        ).first()

        return user_uuid if refresh_token else None

    except JWTError as e:
        print(e)
        return None