import json
import asyncio
from typing import Callable
from typing import Optional
from datetime import datetime, timezone

from fastapi import Depends, Request, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from jose import JWTError, ExpiredSignatureError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from domain.entities.user import User
from shared.exceptions.domain import EmailAlreadyExistsError, UserInactiveError
from infrastructure.database.connection import get_db
from infrastructure.database.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from infrastructure.database.repositories.sqlalchemy_api_key_repository import (
    SQLAlchemyAPIKeyRepository
)
from infrastructure.database.repositories.sqlalchemy_unit_of_work import (
    SQLAlchemyUnitOfWork,
)
from infrastructure.security.api_key_service import APIKeyService
from infrastructure.config.settings import settings
from shared.exceptions.base import UnauthorizedError
from shared.exceptions.application import (
    JWTValidationError,
    ExternalServiceError,
    RepositoryError,
)

import httpx
from cachetools import TTLCache, cached

security = HTTPBearer()
jwks_cache = TTLCache(maxsize=1, ttl=3600)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
optional_bearer = HTTPBearer(auto_error=False)


@cached(cache=jwks_cache)
def get_auth_jwtks():
    try:
        url = f"https://{settings.AUTH0_DOMAIN}/.well-known/jwks.json"
        return httpx.get(url).json()
    except httpx.HTTPError as e:
        raise ExternalServiceError("Auth0", "jwks", str(e))
    except json.JSONDecodeError as e:
        raise ExternalServiceError("Auth0", "jwks", str(e))


def get_user_info(access_token: str) -> dict:
    try:
        url = f"https://{settings.AUTH0_DOMAIN}/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = httpx.get(url, headers=headers)
        response.raise_for_status()

        return response.json()
    except httpx.HTTPError as e:
        raise ExternalServiceError("Auth0", "user_info", str(e))
    except json.JSONDecodeError as e:
        raise ExternalServiceError("Auth0", "user_info", str(e))


async def validate_token(token: str) -> dict:
    try:
        jwks = await asyncio.to_thread(get_auth_jwtks)

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


async def validate_local_user(token: str, db: AsyncSession) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except JWTError as e:
        raise JWTValidationError(str(e))

    user_uuid = payload.get("sub")

    if not user_uuid:
        raise UnauthorizedError("Invalid token: missing user")

    user_repo = SQLAlchemyUserRepository(db)
    user = await user_repo.get_by_uuid(user_uuid)
    if not user:
        raise UnauthorizedError("User not found")

    if not user.is_active:
        raise UserInactiveError()

    return user


async def validate_auth0_user(token: str, db: AsyncSession) -> User:
    try:
        payload = await validate_token(token)

        auth0_user_uuid = payload.get("sub")

        if not auth0_user_uuid:
            raise UnauthorizedError("Invalid token: missing user")

        user_repo = SQLAlchemyUserRepository(db)
        uow = SQLAlchemyUnitOfWork(db)
        user = await user_repo.get_by_auth0_uuid(auth0_user_uuid)

        if user is None:
            user_info = await asyncio.to_thread(get_user_info, token)
            new_user = User(
                auth0_id=auth0_user_uuid,
                name=user_info.get("name") or "",
                email=user_info.get("email"),
                picture=user_info.get("picture"),
                email_verified=bool(user_info.get("email_verified", False)),
                last_login=user_info.get("last_login") or datetime.now(timezone.utc),
            )
            try:
                async with uow:
                    user = await user_repo.create(new_user)
                    await uow.commit()
            except IntegrityError:
                # Carrera: otra petición concurrente ya creó este usuario.
                user = await user_repo.get_by_auth0_uuid(auth0_user_uuid)
                if user is None:
                    # El conflicto no fue por auth0_id: el email ya
                    # pertenece a otra cuenta. No se auto-vincula.
                    raise EmailAlreadyExistsError(user_info.get("email") or "")

        return user

    except SQLAlchemyError as e:
        raise RepositoryError("get_or_create", "User", str(e))


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if payload.get("iss") == "lunance":
            return await validate_local_user(token, db)
    except ExpiredSignatureError:
        raise JWTValidationError("Token expired")
    except JWTError:
        pass

    return await validate_auth0_user(token, db)


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Obtiene el usuario actual y verifica que esté activo."""
    if not current_user.is_active:
        raise UserInactiveError()
    return current_user


async def get_current_active_user_from_url_token(
    token: str,
    db: AsyncSession,
) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if payload.get("iss") == "lunance":
            return await validate_local_user(token, db)
    except ExpiredSignatureError:
        raise JWTValidationError("Token expired")
    except JWTError:
        pass

    return await validate_auth0_user(token, db)

def get_api_key_service(
    db: AsyncSession = Depends(get_db),
) -> APIKeyService:
    return APIKeyService(
        SQLAlchemyAPIKeyRepository(db),
        SQLAlchemyUserRepository(db),
        SQLAlchemyUnitOfWork(db),
    )


async def get_user_dual_auth(
    request: Request,
    api_key: Optional[str] = Security(api_key_header),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(optional_bearer),
    service: APIKeyService = Depends(get_api_key_service),
    db: AsyncSession = Depends(get_db),
) -> User:

    if api_key:
        user, scopes = await service.authenticate(api_key)
        request.state.auth_method = "api_key"
        request.state.api_key_scopes = scopes
        return user

    if credentials:
        request.state.auth_method = "jwt"
        user = await get_current_active_user_from_url_token(credentials.credentials, db)
        if not user.is_active:
            raise UserInactiveError()
        return user

    raise UnauthorizedError("Missing authentication credentials")


def require_scope(scope: str) -> Callable:
    async def checker(
        request: Request,
        user: User = Depends(get_user_dual_auth),
    ) -> User:
        if getattr(request.state, "auth_method", None) == "jwt":
            return user

        scopes = getattr(request.state, "api_key_scopes", [])
        if scope not in scopes:
            raise HTTPException(status_code=403, detail=f"API key missing required scope: {scope}")
        return user
    return checker
