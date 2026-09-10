from fastapi import APIRouter, Depends, HTTPException, Request, Response

from application.auth.commands.login import LoginCommand, LoginHandler
from application.auth.commands.logout import LogoutCommand, LogoutHandler
from application.auth.commands.refresh_token import (
    RefreshTokenCommand,
    RefreshTokenHandler,
)
from application.auth.commands.register import RegisterCommand, RegisterHandler
from domain.entities.user import User
from infrastructure.config.settings import settings
from infrastructure.rate_limiting.limiters import (
    enforce_rate_limit,
    limiter_5_per_hour,
    limiter_10_per_minute,
    limiter_20_per_minute,
    limiter_100_per_minute,
)
from presentation.dependencies import (
    get_login_handler,
    get_logout_handler,
    get_refresh_token_handler,
    get_register_handler,
)
from presentation.dependencies.auth_deps import get_current_active_user
from presentation.schemas.requests.auth import (
    LoginRequest,
    RegisterRequest,
)
from presentation.schemas.responses.auth import (
    RegisterResponse,
    TokenResponse,
    UserInfoResponse,
)

router = APIRouter()


@router.post("/register", response_model=RegisterResponse)
async def register(
    request: Request,
    register_request: RegisterRequest,
    handler: RegisterHandler = Depends(get_register_handler),
):
    enforce_rate_limit(limiter_5_per_hour, request)
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
    enforce_rate_limit(limiter_100_per_minute, request)
    return UserInfoResponse(
        user_uuid=current_user.uuid,
        username=current_user.name,
        is_active=current_user.is_active,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    response: Response,
    login_request: LoginRequest,
    handler: LoginHandler = Depends(get_login_handler),
):
    enforce_rate_limit(limiter_10_per_minute, request)
    command = LoginCommand(
        username=login_request.username, password=login_request.password
    )

    result = await handler.handle(command)

    response.set_cookie(
        key="refresh_token",
        value=result.refresh_token,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN or None,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/v2/auth",
    )

    return TokenResponse(
        access_token=result.access_token,
        token_type=result.token_type,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    handler: RefreshTokenHandler = Depends(get_refresh_token_handler),
):
    enforce_rate_limit(limiter_20_per_minute, request)
    incoming_token = request.cookies.get("refresh_token")
    if not incoming_token:
        raise HTTPException(status_code=401, detail="Refresh token not found")

    command = RefreshTokenCommand(refresh_token=incoming_token)
    result = await handler.handle(command)

    response.set_cookie(
        key="refresh_token",
        value=result.refresh_token,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN or None,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/v2/auth",
    )

    return TokenResponse(access_token=result.access_token, token_type=result.token_type)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    handler: LogoutHandler = Depends(get_logout_handler),
):
    enforce_rate_limit(limiter_10_per_minute, request)
    incoming_token = request.cookies.get("refresh_token")

    if not incoming_token:
        raise HTTPException(status_code=401, detail="Refresh token not found")

    await handler.handle(LogoutCommand(refresh_token=incoming_token))

    response.delete_cookie(
        key="refresh_token",
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN or None,
        path="/api/v2/auth",
    )

    return {"message": "Logout exitoso"}
