from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from domain.repositories.user_repository import UserRepository
from domain.repositories.auth_token_repository import AuthTokenRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from application.interfaces.auth_service import AuthTokenServiceInterface, AuthConfig
from shared.exceptions.application import CommandValidationError
from shared.exceptions.domain import (
    UserInactiveError,
    InvalidCredentialsError,
)


@dataclass
class LoginCommand:
    username: str
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
        jwt_service: AuthTokenServiceInterface,
        uow: AbstractUnitOfWork,
        auth_config: AuthConfig,
    ):
        self.user_repository = user_repo
        self.auth_token_repository = auth_token_repo
        self.jwt_service = jwt_service
        self.uow = uow
        self.auth_config = auth_config

    async def handle(self, command: LoginCommand) -> LoginResponse:
        if not command.username or not command.password:
            raise CommandValidationError(
                "LoginCommand", ["Nombre de usuario y contraseña son requeridos"]
            )

        user = await self.user_repository.get_by_username(command.username)
        if not user:
            raise InvalidCredentialsError("username")

        if not user.is_active:
            raise UserInactiveError()

        if not self.jwt_service.check_password(command.password, user.password):
            raise InvalidCredentialsError("password")

        access_token = self.jwt_service.create_access_token(
            user_uuid=user.uuid, expires_in=self.auth_config.access_token_expire_minutes
        )
        refresh_token = self.jwt_service.create_refresh_token(
            user_uuid=user.uuid, expires_in=self.auth_config.refresh_token_expire_days
        )

        refresh_token_hash = self.jwt_service.hash_refresh_token(refresh_token)
        refresh_expires_at = datetime.now(timezone.utc) + timedelta(
            days=self.auth_config.refresh_token_expire_days
        )

        async with self.uow:
            await self.auth_token_repository.save_refresh_token(
                user_id=user.id,
                refresh_hash_token=refresh_token_hash,
                expires_at=refresh_expires_at,
            )
            await self.uow.commit()

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=timedelta(minutes=self.auth_config.access_token_expire_minutes),
        )
