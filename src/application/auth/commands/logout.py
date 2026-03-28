from dataclasses import dataclass
from typing import cast

from domain.repositories.user_repository import UserRepository
from domain.repositories.auth_token_repository import AuthTokenRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from application.interfaces.auth_service import AuthTokenServiceInterface
from shared.exceptions.application import CommandValidationError


@dataclass
class LogoutCommand:
    refresh_token: str


@dataclass
class LogoutResponse:
    message: str = "Logout exitoso"


class LogoutHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        auth_token_repository: AuthTokenRepository,
        jwt_service: AuthTokenServiceInterface,
        uow: AbstractUnitOfWork,
    ):
        self.user_repository = user_repository
        self.jwt_service = jwt_service
        self.auth_token_repository = auth_token_repository
        self.uow = uow

    async def handle(self, command: LogoutCommand) -> LogoutResponse:
        if not command.refresh_token:
            raise CommandValidationError(
                "LogoutCommand", ["Refresh token es requerido"]
            )

        user_uuid = await self.jwt_service.verify_refresh_token(command.refresh_token)
        if not user_uuid:
            return LogoutResponse()

        # Obtener user_id para revocar el token
        user = await self.user_repository.get_by_uuid(user_uuid)
        if not user:
            return LogoutResponse()

        refresh_token_hash = self.jwt_service.hash_refresh_token(command.refresh_token)
        async with self.uow:
            await self.auth_token_repository.revoke_refresh_token(
                cast(int, user.id), refresh_token_hash
            )
            await self.uow.commit()

        return LogoutResponse()
