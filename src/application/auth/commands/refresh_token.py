from dataclasses import dataclass
from datetime import timedelta, datetime, timezone
from typing import cast

from domain.repositories.user_repository import UserRepository
from domain.repositories.auth_token_repository import AuthTokenRepository
from application.interfaces.auth_service import AuthTokenServiceInterface, AuthConfig
from shared.exceptions.application import CommandValidationError
from shared.exceptions.application import JWTValidationError
from application.auth.commands.login import LoginResponse
from domain.repositories.unit_of_work import AbstractUnitOfWork


@dataclass
class RefreshTokenCommand:
    refresh_token: str


@dataclass
class RefreshTokenHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        auth_token_repository: AuthTokenRepository,
        jwt_service: AuthTokenServiceInterface,
        uow: AbstractUnitOfWork,
        auth_config: AuthConfig,
    ):
        self.user_repository = user_repository
        self.auth_token_repository = auth_token_repository
        self.jwt_service = jwt_service
        self.uow = uow
        self.auth_config = auth_config

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

        user = await self.user_repository.get_by_uuid(cast(str, user_uuid))
        if not user or not user.is_active:
            raise CommandValidationError("RefreshTokenCommand", ["User inválido"])

        refresh_token_hash = self.jwt_service.hash_refresh_token(command.refresh_token)
        stored_token = await self.auth_token_repository.get_refresh_token(
            cast(int, user.id), refresh_token_hash
        )

        if not stored_token:
            raise CommandValidationError(
                "RefreshTokenCommand", ["Refresh token inválido"]
            )

        access_token = self.jwt_service.create_access_token(
            user_uuid=cast(str, user_uuid),
            expires_in=self.auth_config.access_token_expire_minutes,
        )

        new_refresh_token = self.jwt_service.create_refresh_token(
            user_uuid=cast(str, user_uuid)
        )
        new_refresh_token_hash = self.jwt_service.hash_refresh_token(new_refresh_token)
        new_expires_at = datetime.now(tz=timezone.utc) + timedelta(
            days=self.auth_config.refresh_token_expire_days
        )

        async with self.uow:
            await self.auth_token_repository.save_refresh_token(
                user_id=cast(int, user.id),
                refresh_hash_token=new_refresh_token_hash,
                expires_at=new_expires_at,
            )
            await self.uow.commit()

        return LoginResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=timedelta(minutes=self.auth_config.access_token_expire_minutes),
        )
