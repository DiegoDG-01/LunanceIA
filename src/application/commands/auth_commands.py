from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from domain.entities.user import User
from domain.repositories.user_repository import UserRepository
from infrastructure.security.auth_service import verify_password, create_access_token, create_refresh_token
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
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository


    async def handle(self, command: LoginCommand) -> LoginResponse:
        if not command.email or not command.password:
            raise CommandValidationError("LoginCommand", ["Email y contraseña son requeridos"])

        user = await self.user_repository.get_by_email(command.email)
        if not user:
            raise UserNotFoundError(email=command.email)

        if not user.is_active:
            raise UserInactiveError()

        if not verify_password(command.password, user.password_hash):
            raise CommandValidationError("LoginCommand", ["Credenciales incorrectas"])

        token_data = {"sub": str(user.uuid)}
        access_token = create_access_token(data=token_data, expires_delta=timedelta(hours=1))
        refresh_token = create_refresh_token(data=token_data, expires_delta=timedelta(days=30))

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=timedelta(hours=1)
        )


@dataclass
class RefreshTokenCommand:
    refresh_token: str


@dataclass
class RefreshTokenHandler:

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository


    async def handle(self, command: RefreshTokenCommand) -> LoginResponse:
        """Ejecuta el comando de refresh token."""
        from infrastructure.security.auth_service import verify_refresh_token
        from infrastructure.database.connection import get_db

        # Verificar refresh token (necesitas adaptar esto a tu lógica actual)
        # user_uuid = verify_refresh_token(command.refresh_token, db)

        # Por ahora, implementación simplificada
        # TODO: Implementar lógica completa de refresh token

        raise NotImplementedError("Refresh token handler pendiente de implementar")

