from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.users.user import User
from infrastructure.config.settings import settings
from infrastructure.database.connection import get_db
from infrastructure.database.repositories.sqlalchemy_api_key_repository import (
    SQLAlchemyAPIKeyRepository,
)
from infrastructure.database.repositories.sqlalchemy_unit_of_work import (
    SQLAlchemyUnitOfWork,
)
from infrastructure.database.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from infrastructure.rate_limiting.client_ip import ip_identity
from infrastructure.rate_limiting.limiters import (
    enforce_rate_limit,
    limiter_auth_failure,
)
from infrastructure.security.api_key_service import APIKeyService
from shared.exceptions.application import JWTValidationError
from shared.exceptions.base import UnauthorizedError
from shared.exceptions.domain import UserInactiveError

security = HTTPBearer()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
optional_bearer = HTTPBearer(auto_error=False)


async def validate_local_user(token: str, db: AsyncSession) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except ExpiredSignatureError:
        raise JWTValidationError("Token expired")
    except JWTError as e:
        raise JWTValidationError(str(e))
    if payload.get("iss") != "lunance":
        raise JWTValidationError("Invalid token issuer")

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


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await validate_local_user(credentials.credentials, db)
    except (UnauthorizedError, JWTValidationError):
        await _throttle_auth_failure(request)
        raise


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
    return await validate_local_user(token, db)


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
    api_key: str | None = Security(api_key_header),
    credentials: HTTPAuthorizationCredentials | None = Security(optional_bearer),
    service: APIKeyService = Depends(get_api_key_service),
    db: AsyncSession = Depends(get_db),
) -> User:
    if api_key:
        try:
            user, scopes = await service.authenticate(api_key)
        except UnauthorizedError:
            await _throttle_auth_failure(request)
            raise
        request.state.auth_method = "api_key"
        request.state.api_key_scopes = scopes
        # Identificador para rate limiting por usuario (no por IP): el tráfico
        # vía MCP llega siempre como 127.0.0.1 y compartiría un solo bucket.
        request.state.rate_limit_id = f"user:{user.id}"
        return user

    if credentials:
        try:
            user = await get_current_active_user_from_url_token(
                credentials.credentials, db
            )
            if not user.is_active:
                raise UserInactiveError()
        except (UnauthorizedError, JWTValidationError, UserInactiveError):
            await _throttle_auth_failure(request)
            raise

        request.state.auth_method = "jwt"
        request.state.rate_limit_id = f"user:{user.id}"
        return user

    await _throttle_auth_failure(request)
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
            raise HTTPException(
                status_code=403, detail=f"API key missing required scope: {scope}"
            )
        return user

    return checker


async def _throttle_auth_failure(request: Request) -> None:
    """Limita los intentos de auth inválidos por IP (M2): evita el flooding
    no autenticado contra la capa de auth + BD. Lanza 429 si se supera."""
    await enforce_rate_limit(
        limiter_auth_failure, request, key=f"auth_failure:{ip_identity(request)}"
    )
