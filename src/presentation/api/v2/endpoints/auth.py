from fastapi import APIRouter, Depends, Request

from domain.entities.user import User
from presentation.schemas.requests.auth import (
    LoginRequest,
    RegisterRequest,
    RefreshTokenRequest,
)
from presentation.schemas.responses.auth import (
    TokenResponse,
    RegisterResponse,
    UserInfoResponse,
)
from presentation.dependencies.auth_deps import get_current_active_user
from presentation.dependencies import (
    get_login_handler,
    get_register_handler,
    get_refresh_token_handler,
    get_logout_handler,
)
from application.auth.commands.login import LoginCommand, LoginHandler
from application.auth.commands.refresh_token import (
    RefreshTokenCommand,
    RefreshTokenHandler,
)
from application.auth.commands.logout import LogoutCommand, LogoutHandler
from application.auth.commands.register import RegisterCommand, RegisterHandler

from infrastructure.rate_limiting.limiters import (
    enforce_rate_limit,
    limiter_5_per_hour,
    limiter_100_per_minute,
    limiter_10_per_minute,
    limiter_20_per_minute,
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
    login_request: LoginRequest,
    handler: LoginHandler = Depends(get_login_handler),
):
    enforce_rate_limit(limiter_10_per_minute, request)
    command = LoginCommand(
        username=login_request.username, password=login_request.password
    )

    result = await handler.handle(command)
    return TokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type=result.token_type,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    refresh_request: RefreshTokenRequest,
    handler: RefreshTokenHandler = Depends(get_refresh_token_handler),
):
    enforce_rate_limit(limiter_20_per_minute, request)
    command = RefreshTokenCommand(refresh_token=refresh_request.refresh_token)

    result = await handler.handle(command)
    return TokenResponse(
        access_token=result.access_token, refresh_token=result.refresh_token
    )


@router.post("/logout")
async def logout(
    request: Request,
    logout_request: RefreshTokenRequest,
    handler: LogoutHandler = Depends(get_logout_handler),
):
    enforce_rate_limit(limiter_10_per_minute, request)
    command = LogoutCommand(refresh_token=logout_request.refresh_token)

    await handler.handle(command)
    return {"message": "Logout exitoso"}
