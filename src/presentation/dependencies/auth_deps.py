from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.users.user import User
from infrastructure.database.connection import get_db
from infrastructure.database.repositories.sqlalchemy_api_key_repository import (
    SQLAlchemyAPIKeyRepository,
)
from infrastructure.database.repositories.sqlalchemy_session_repository import (
    SQLAlchemySessionRepository,
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
from presentation.dependencies.auth_services import (
    build_session_revocations,
    get_token_issuer,
)
from shared.exceptions.application import JWTValidationError
from shared.exceptions.base import UnauthorizedError
from shared.exceptions.domain import SessionExpiredError, UserInactiveError

security = HTTPBearer()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
optional_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AccessContext:
    """Usuario del access token y la sesión (`sid`) desde la que llega la petición."""

    user: User
    session_uuid: str


async def authenticate_access_token(token: str, db: AsyncSession) -> AccessContext:
    """Único camino para un access token: firma, sesión no revocada y usuario activo."""
    claims = get_token_issuer().verify(token)

    # La sesión pudo cerrarse desde otro dispositivo: su access token sigue firmado y vigente
    # hasta 10 min, así que se comprueba en cada petición (Redis y, si no está, MySQL).
    revocations = build_session_revocations(SQLAlchemySessionRepository(db))
    if await revocations.is_revoked(claims.session_uuid):
        raise SessionExpiredError()

    user = await SQLAlchemyUserRepository(db).get_by_uuid(claims.user_uuid)
    if not user:
        raise UnauthorizedError("User not found")
    if not user.is_active:
        raise UserInactiveError()

    return AccessContext(user=user, session_uuid=claims.session_uuid)


async def get_access_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> AccessContext:
    try:
        context = await authenticate_access_token(credentials.credentials, db)
    except (UnauthorizedError, JWTValidationError):
        await _throttle_auth_failure(request)
        raise
    request.state.session_uuid = context.session_uuid
    return context


async def get_current_user(
    context: AccessContext = Depends(get_access_context),
) -> User:
    return context.user


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
    return (await authenticate_access_token(token, db)).user


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
