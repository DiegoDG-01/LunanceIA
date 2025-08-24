from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

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
from presentation.dependencies.service_deps import (
    get_login_handler,
    get_register_handler,
    get_refresh_token_handler,
    get_logout_handler,
)
from application.commands.auth_commands import (
    LoginCommand,
    LoginHandler,
    RefreshTokenCommand,
    RefreshTokenHandler,
    LogoutCommand,
    LogoutHandler,
)
from application.commands.register_commands import RegisterCommand, RegisterHandler

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=RegisterResponse)
@limiter.limit("1000/minute")  # 3 registros por hora por IP
async def register(
    request: Request,
    register_request: RegisterRequest,
    handler: RegisterHandler = Depends(get_register_handler),
):
    command = RegisterCommand(
        name=register_request.name,
        email=register_request.email,
        password=register_request.password,
    )

    result = await handler.handle(command)
    return RegisterResponse(
        user_uuid=result.user_uuid,
        name=result.name,
        email=result.email,
        message=result.message,
    )


@router.get("/me", response_model=UserInfoResponse)
@limiter.limit("1000/minute")
async def me(request: Request, current_user: User = Depends(get_current_active_user)):
    return UserInfoResponse(
        user_uuid=current_user.uuid,
        name=current_user.name,
        email=current_user.email,
        is_active=current_user.is_active,
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("1000/minute")
async def login(
    request: Request,
    login_request: LoginRequest,
    handler: LoginHandler = Depends(get_login_handler),
):
    command = LoginCommand(email=login_request.email, password=login_request.password)

    result = await handler.handle(command)
    return TokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type=result.token_type,
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("1000/minute")
async def refresh_token(
    request: Request,
    refresh_request: RefreshTokenRequest,
    handler: RefreshTokenHandler = Depends(get_refresh_token_handler),
):
    command = RefreshTokenCommand(refresh_token=refresh_request.refresh_token)

    result = await handler.handle(command)
    return TokenResponse(
        access_token=result.access_token, refresh_token=result.refresh_token
    )


@router.post("/logout")
@limiter.limit("1000/minute")
async def logout(
    request: Request,
    logout_request: RefreshTokenRequest,
    handler: LogoutHandler = Depends(get_logout_handler),
):
    command = LogoutCommand(refresh_token=logout_request.refresh_token)

    await handler.handle(command)
    return {"message": "Logout exitoso"}
