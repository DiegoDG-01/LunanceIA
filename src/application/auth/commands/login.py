from pydantic import EmailStr
from dataclasses import dataclass
from datetime import datetime, timedelta

from domain.repositories.user_repository import UserRepository
from domain.repositories.auth_token_repository import AuthTokenRepository
from infrastructure.config.settings import settings
from infrastructure.security.jwt_service import JWTService
from shared.exceptions.application import CommandValidationError
from shared.exceptions.domain import (
    UserInactiveError,
    InvalidCredentialsError,
)


@dataclass
class LoginCommand:
    email: EmailStr
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
                "LoginCommand", ["Email y contraseña son requeridos"]
            )

        user = await self.user_repository.get_by_email(command.email)
        if not user:
            raise InvalidCredentialsError("51")

        if not user.is_active:
            raise UserInactiveError()

        if not self.jwt_service.check_password(command.password, user.password_hash):
            raise InvalidCredentialsError("57")

        access_token = self.jwt_service.create_access_token(
            user_uuid=user.uuid, expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        refresh_token = self.jwt_service.create_refresh_token(
            user_uuid=user.uuid, expires_in=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        refresh_token_hash = self.jwt_service.hash_refresh_token(refresh_token)
        refresh_expires_at = datetime.now() + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        await self.auth_token_repository.save_refresh_token(
            user_id=user.id,
            refresh_hash_token=refresh_token_hash,
            expires_at=refresh_expires_at,
        )

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=timedelta(hours=1),
        )
