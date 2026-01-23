from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from domain.entities.user import User
from shared.exceptions.domain import UserInactiveError
from infrastructure.database.connection import get_db
from infrastructure.database.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from infrastructure.config.settings import settings
from shared.exceptions.base import UnauthorizedError
from shared.exceptions.application import JWTValidationError

import httpx
from cachetools import TTLCache, cached

security = HTTPBearer()
jwks_cache = TTLCache(maxsize=1, ttl=3600)


@cached(cache=jwks_cache)
def get_auth_jwtks():
    url = f"https://{settings.AUTH0_DOMAIN}/.well-known/jwks.json"
    return httpx.get(url).json()


def get_user_ifno(access_token: str) -> dict:
    url = f"https://{settings.AUTH0_DOMAIN}/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = httpx.get(url, headers=headers)
    return response.json()


def validate_token(token: str) -> dict:
    try:
        jwks = get_auth_jwtks()

        unverified_header = jwt.get_unverified_header(token)

        rsa_key = []
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"],
                }
                break

        if not rsa_key:
            raise UnauthorizedError("Invalid token")

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.AUTH0_AUDIENCE,
            issuer=f"https://{settings.AUTH0_DOMAIN}/",
        )

        return payload

    except JWTError:
        raise JWTValidationError("Invalid token")
    except Exception:
        raise UnauthorizedError("Authentication failed")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    try:
        token = credentials.credentials

        payload = validate_token(token)

        auth0_user_uuid = payload.get("sub")

        if not auth0_user_uuid:
            raise UnauthorizedError("Invalid token: missing user")

        user_repo = SQLAlchemyUserRepository(db)
        user = await user_repo.get_by_auth0_uuid(auth0_user_uuid)

        if user is None:
            user_info = get_user_ifno(token)
            new_user = User(
                auth0_id=auth0_user_uuid,
                name=user_info.get("name"),
                email=user_info.get("email"),
                picture=user_info.get("picture"),
                email_verified=user_info.get("email_verified"),
                last_login=user_info.get("last_login"),
            )
            user = user_repo.create(new_user)

        return user

    except JWTValidationError:
        raise JWTValidationError("Invalid token")
    except Exception:
        raise UnauthorizedError("Authentication failed")


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Obtiene el usuario actual y verifica que esté activo."""
    if not current_user.is_active:
        raise UserInactiveError()
    return current_user
