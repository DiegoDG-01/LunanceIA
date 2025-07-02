from fastapi import APIRouter, Depends, HTTPException, status

from domain.entities.user import User
from presentation.schemas.requests.auth import LoginRequest, RegisterRequest, RefreshTokenRequest
from presentation.schemas.responses.auth import TokenResponse, RegisterResponse, UserInfoResponse
from presentation.dependencies.auth_deps import get_current_active_user
from presentation.dependencies.service_deps import (
    get_login_handler,
    get_register_handler,
    get_refresh_token_handler
)
from application.commands.auth_commands import LoginCommand, LoginHandler, RefreshTokenCommand, RefreshTokenHandler
from application.commands.register_commands import RegisterCommand, RegisterHandler
from shared.exceptions.domain import (
    UserNotFoundError,
    UserInactiveError,
    EmailAlreadyExistsError
)
from shared.exceptions.application import CommandValidationError
from shared.exceptions.base import ValidationError

router = APIRouter()

@router.post("/login", response_model=TokenResponse)
async def login(
        request: LoginRequest,
        handler: LoginHandler = Depends(get_login_handler)
):
    command = LoginCommand(
        email=request.email,
        password=request.password
    )

    try:
        result = await handler.handle(command)
        return TokenResponse(
            access_token=result.access_token,
            refresh_token=result.refresh_token,
            token_type=result.token_type
        )
    except (UserNotFoundError, UserInactiveError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas"
        )
    except CommandValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )



@router.post("/register", response_model=RegisterResponse)
async def register(
        request: RegisterRequest,
        handler: RegisterHandler = Depends(get_register_handler)
):
    command = RegisterCommand(
        name=request.name,
        email=request.email,
        password=request.password,
    )

    try:
        result = await handler.handle(command)
        return RegisterResponse(
            user_id=result.user_id,
            name=result.name,
            email=result.email,
            message=result.message
        )
    except EmailAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message
        )
    except CommandValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
        request: RefreshTokenRequest,
        handler: RefreshTokenHandler = Depends(get_refresh_token_handler)
):
    command = RefreshTokenCommand(
        refresh_token=request.refresh_token
    )

    try:
        result = await handler.handle(command)
        return TokenResponse(
            access_token=result.access_token,
            refresh_token=result.refresh_token
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalido"
        )

@router.get("/me", response_model=UserInfoResponse)
async def me(
        current_user: User = Depends(get_current_active_user)
):
    return UserInfoResponse(
        user_id=current_user.user_id,
        name=current_user.name,
        email=current_user.email
    )


@router.post("/logout")
async def logout():
    """Cerrar sesión (invalidar tokens)."""
    # TODO: Implementar lógica de logout (blacklist de tokens)
    return {
        "message": "Logout successful"
    }
