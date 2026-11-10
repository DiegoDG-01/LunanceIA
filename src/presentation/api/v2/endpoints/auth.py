from dataclasses import replace
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from application.auth.commands.login import LoginCommand, LoginHandler
from application.auth.commands.logout import LogoutCommand, LogoutHandler
from application.auth.commands.refresh_session import (
    RefreshSessionCommand,
    RefreshSessionHandler,
)
from application.auth.commands.register import RegisterCommand, RegisterHandler
from application.auth.commands.revoke_session import (
    RevokeSessionCommand,
    RevokeSessionHandler,
)
from application.auth.dto import ClientContext, IssuedSession
from application.auth.queries.list_sessions import (
    ListSessionsHandler,
    ListSessionsQuery,
)
from domain.entities.auth.session import Platform
from domain.entities.users.user import User
from infrastructure.cache.redis import claim_once
from infrastructure.config.settings import settings
from infrastructure.rate_limiting.client_ip import ip_identity
from infrastructure.rate_limiting.limiters import (
    enforce_rate_limit,
    limiter_5_per_hour,
    limiter_10_per_minute,
    limiter_20_per_minute,
    limiter_30_per_minute,
    limiter_100_per_minute,
)
from presentation.dependencies import (
    get_list_sessions_handler,
    get_login_handler,
    get_logout_handler,
    get_refresh_session_handler,
    get_register_handler,
    get_revoke_session_handler,
)
from presentation.dependencies.auth_deps import (
    AccessContext,
    get_access_context,
    get_current_active_user,
)
from presentation.dependencies.client_deps import (
    get_client_context,
    get_device_context,
)
from presentation.schemas.requests.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
)
from presentation.schemas.responses.auth import (
    LogoutResponse,
    RegisterResponse,
    SessionResponse,
    TokenResponse,
    UserInfoResponse,
)
from shared.utils.time import utc_now

router = APIRouter()

REFRESH_COOKIE = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v2/auth"
# Un rate limit cortando el login se audita una vez por IP y minuto, no en cada intento.
THROTTLED_AUDIT_WINDOW_SECONDS = 60


def _set_refresh_cookie(response: Response, issued: IssuedSession) -> None:
    max_age = round((issued.session.expires_at - utc_now()).total_seconds())
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=issued.refresh_token,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN or None,
        max_age=max(max_age, 0),
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN or None,
        path=REFRESH_COOKIE_PATH,
    )


def _token_response(response: Response, issued: IssuedSession) -> TokenResponse:
    """Web: el refresh va en la cookie httpOnly. ios/android: en el body."""
    token = TokenResponse(
        access_token=issued.access_token,
        token_type=issued.token_type,
        expires_in=issued.expires_in,
    )
    if issued.session.platform is Platform.WEB:
        _set_refresh_cookie(response, issued)
    else:
        token.refresh_token = issued.refresh_token
    return token


def _incoming_refresh_token(
    request: Request, context: ClientContext, body_token: str | None
) -> str:
    token = (
        request.cookies.get(REFRESH_COOKIE)
        if context.platform is Platform.WEB
        else body_token
    )
    if not token:
        raise HTTPException(status_code=401, detail="Refresh token not found")
    return token


@router.post("/register", response_model=RegisterResponse)
async def register(
    request: Request,
    register_request: RegisterRequest,
    handler: RegisterHandler = Depends(get_register_handler),
):
    await enforce_rate_limit(limiter_5_per_hour, request, fail_closed=True)
    command = RegisterCommand(
        username=register_request.username,
        password=register_request.password,
    )

    result = await handler.handle(command)
    return RegisterResponse(
        user_uuid=result.user_uuid,
        username=result.username,
        message=result.message,
    )


@router.get("/me", response_model=UserInfoResponse)
async def me(request: Request, current_user: User = Depends(get_current_active_user)):
    await enforce_rate_limit(limiter_100_per_minute, request)
    return UserInfoResponse(
        user_uuid=current_user.uuid,
        username=current_user.name,
        is_active=current_user.is_active,
    )


@router.post("/login", response_model=TokenResponse, response_model_exclude_none=True)
async def login(
    request: Request,
    response: Response,
    login_request: LoginRequest,
    context: ClientContext = Depends(get_device_context),
    handler: LoginHandler = Depends(get_login_handler),
):
    command = LoginCommand(
        username=login_request.username,
        password=login_request.password,
        context=replace(context, device_name=login_request.device_name),
    )
    try:
        await enforce_rate_limit(limiter_10_per_minute, request, fail_closed=True)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS and await claim_once(
            f"audit:login_throttled:{ip_identity(request)}",
            THROTTLED_AUDIT_WINDOW_SECONDS,
        ):
            await handler.record_throttled(command)
        raise

    issued = await handler.handle(command)
    return _token_response(response, issued)


@router.post("/refresh", response_model=TokenResponse, response_model_exclude_none=True)
async def refresh_token(
    request: Request,
    response: Response,
    body: RefreshRequest | None = None,
    context: ClientContext = Depends(get_device_context),
    handler: RefreshSessionHandler = Depends(get_refresh_session_handler),
):
    await enforce_rate_limit(limiter_20_per_minute, request)
    token = _incoming_refresh_token(
        request, context, body.refresh_token if body else None
    )

    issued = await handler.handle(
        RefreshSessionCommand(refresh_token=token, context=context)
    )
    return _token_response(response, issued)


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    response: Response,
    body: LogoutRequest | None = None,
    context: ClientContext = Depends(get_client_context),
    handler: LogoutHandler = Depends(get_logout_handler),
):
    await enforce_rate_limit(limiter_10_per_minute, request)
    body = body or LogoutRequest()
    token = _incoming_refresh_token(request, context, body.refresh_token)

    await handler.handle(
        LogoutCommand(
            refresh_token=token, all_devices=body.all_devices, context=context
        )
    )

    if context.platform is Platform.WEB:
        _clear_refresh_cookie(response)
    return LogoutResponse()


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    request: Request,
    auth: AccessContext = Depends(get_access_context),
    handler: ListSessionsHandler = Depends(get_list_sessions_handler),
):
    await enforce_rate_limit(limiter_30_per_minute, request)
    views = await handler.handle(
        ListSessionsQuery(
            user_id=cast(int, auth.user.id),
            current_session_uuid=auth.session_uuid,
        )
    )
    return [
        SessionResponse(
            uuid=view.session.uuid,
            platform=view.session.platform.value,
            device_name=view.session.device_name,
            client=view.session.client,
            created_at=view.session.created_at,
            last_seen_at=view.session.last_seen_at,
            last_ip=view.session.last_ip,
            is_current=view.is_current,
        )
        for view in views
    ]


@router.delete("/sessions/{session_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    request: Request,
    session_uuid: UUID,
    auth: AccessContext = Depends(get_access_context),
    context: ClientContext = Depends(get_client_context),
    handler: RevokeSessionHandler = Depends(get_revoke_session_handler),
):
    await enforce_rate_limit(limiter_20_per_minute, request)
    await handler.handle(
        RevokeSessionCommand(
            user_id=cast(int, auth.user.id),
            session_uuid=str(session_uuid),
            actor_session_uuid=auth.session_uuid,
            context=context,
        )
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
