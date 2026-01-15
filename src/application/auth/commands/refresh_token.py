from dataclasses import dataclass
from datetime import timedelta

from domain.repositories.user_repository import UserRepository
from domain.repositories.auth_token_repository import AuthTokenRepository
from infrastructure.config.settings import settings
from infrastructure.security.jwt_service import JWTService
from shared.exceptions.application import CommandValidationError
from shared.exceptions.application import JWTValidationError
from application.auth.commands.login import LoginResponse


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

        try:
            user_uuid = await self.jwt_service.verify_refresh_token(
                command.refresh_token
            )
        except JWTValidationError:
            raise CommandValidationError(
                "RefreshTokenCommand", ["Refresh token inválido"]
            )

        user = await self.user_repository.get_by_uuid(user_uuid)
        if not user or not user.is_active:
            raise CommandValidationError("RefreshTokenCommand", ["User inválido"])

        refresh_token_hash = self.jwt_service.hash_refresh_token(command.refresh_token)
        stored_token = await self.auth_token_repository.get_refresh_token(
            user.id, refresh_token_hash
        )

        if not stored_token:
            raise CommandValidationError(
                "RefreshTokenCommand", ["Refresh token inválido"]
            )

        access_token = self.jwt_service.create_access_token(
            user_uuid=user_uuid, expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

        return LoginResponse(
            access_token=access_token,
            refresh_token=command.refresh_token,
            expires_in=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
