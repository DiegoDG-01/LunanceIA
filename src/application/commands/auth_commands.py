from dataclasses import dataclass
from datetime import datetime, timedelta

from domain.repositories.user_repository import UserRepository
from domain.repositories.auth_token_repository import AuthTokenRepository
from infrastructure.config.settings import settings
from infrastructure.security.jwt_service import JWTService
from shared.exceptions.application import CommandValidationError
from shared.exceptions.domain import UserNotFoundError, UserInactiveError


@dataclass
class LoginCommand:
    email: str
    password: str


@dataclass
class LoginResponse:
    access_token: str
    refresh_token: str
    expires_in: timedelta
    token_type: str = "bearer"


class LoginHandler:
    def __init__(
        self,
        user_repo: UserRepository,
        auth_token_repo: AuthTokenRepository,
        jwt_service: JWTService,
    ):
        self.user_repository = user_repo
        self.auth_token_repository = auth_token_repo
        self.jwt_service = jwt_service

    async def handle(self, command: LoginCommand) -> LoginResponse:
        if not command.email or not command.password:
            raise CommandValidationError(
                "LoginCommand", ["Email y contraseña son requeridos"]
            )

        user = await self.user_repository.get_by_email(command.email)
        if not user:
            raise UserNotFoundError(email=command.email)

        if not user.is_active:
            raise UserInactiveError()

        if not self.jwt_service.check_password(command.password, user.password_hash):
            raise CommandValidationError("LoginCommand", ["Credenciales incorrectas"])

        access_token = self.jwt_service.create_access_token(
            user_id=user.uuid, expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        refresh_token = self.jwt_service.create_refresh_token(
            user_id=user.uuid, expires_in=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        refresh_token_hash = self.jwt_service.hash_refresh_token(refresh_token)
        refresh_expires_at = datetime.now() + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        await self.auth_token_repository.save_refresh_token(
            user_uuid=user.uuid,
            refresh_hash_token=refresh_token_hash,
            expires_at=refresh_expires_at,
        )

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=timedelta(hours=1),
        )


@dataclass
class RefreshTokenCommand:
    refresh_token: str


@dataclass
class RefreshTokenHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        auth_token_repository: AuthTokenRepository,
        jwt_service: JWTService,
    ):
        self.user_repository = user_repository
        self.auth_token_repository = auth_token_repository
        self.jwt_service = jwt_service

    async def handle(self, command: RefreshTokenCommand) -> LoginResponse:
        if not command.refresh_token:
            raise CommandValidationError(
                "RefreshTokenCommand", ["Refresh token es requerido"]
            )

        user_uuid = self.jwt_service.verify_refresh_token(command.refresh_token)

        if not user_uuid:
            raise CommandValidationError(
                "RefreshTokenCommand", ["Refresh token invalido"]
            )

        refresh_token_hash = self.jwt_service.hash_refresh_token(command.refresh_token)
        stored_token = await self.auth_token_repository.get_refresh_token(
            user_uuid, refresh_token_hash
        )

        if not stored_token:
            raise CommandValidationError(
                "RefreshTokenCommand", ["Refresh token invalido"]
            )

        user = await self.user_repository.get_by_uuid(user_uuid)
        if not user or not user.is_active:
            raise CommandValidationError("RefreshTokenCommand", ["User invalido"])

        access_token = self.jwt_service.create_access_token(
            user_id=user_uuid, expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

        return LoginResponse(
            access_token=access_token,
            refresh_token=command.refresh_token,
            expires_in=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )


@dataclass
class LogoutCommand:
    refresh_token: str


@dataclass
class LogoutResponse:
    message: str = "Logout exitoso"


class LogoutHandler:
    def __init__(
        self, auth_token_repository: AuthTokenRepository, jwt_service: JWTService
    ):
        self.jwt_service = jwt_service
        self.auth_token_repository = auth_token_repository

    async def handle(self, command: LogoutCommand) -> LogoutResponse:
        if not command.refresh_token:
            raise CommandValidationError(
                "LogoutCommand", ["Refresh token es requerido"]
            )

        user_uuid = self.jwt_service.verify_refresh_token(command.refresh_token)
        if not user_uuid:
            return LogoutResponse()

        refresh_token_hash = self.jwt_service.hash_refresh_token(command.refresh_token)
        await self.auth_token_repository.revoke_refresh_token(
            user_uuid, refresh_token_hash
        )

        return LogoutResponse()
