from dataclasses import dataclass
from typing import Optional

from domain.entities.user import User
from domain.repositories.user_repository import UserRepository
from infrastructure.security.auth_service import get_password_hash
from shared.exceptions.domain import EmailAlreadyExistsError
from shared.exceptions.application import CommandValidationError
from shared.validators.business import UserValidator


@dataclass
class RegisterCommand:
    """Comando para registro de usuario."""
    name: str
    email: str
    password: str


@dataclass
class RegisterResponse:
    """Respuesta del comando de registro."""
    user_id: int
    name: str
    email: str
    message: str


class RegisterHandler:
    """Handler para registro de usuario."""

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def handle(self, command: RegisterCommand) -> RegisterResponse:
        """Ejecuta el comando de registro."""
        # Validar entrada
        UserValidator.validate_email(command.email)
        UserValidator.validate_password(command.password)

        if not command.name or not command.name.strip():
            raise CommandValidationError("RegisterCommand", ["El nombre es requerido"])

        # Verificar que el email no exista
        existing_user = await self.user_repository.get_by_email(command.email)
        if existing_user:
            raise EmailAlreadyExistsError(command.email)

        # Crear usuario
        password_hash = get_password_hash(command.password)
        user = User.create_new(
            name=command.name.strip(),
            email=command.email.lower(),
            password_hash=password_hash
        )

        # Guardar usuario
        saved_user = await self.user_repository.create(user)

        return RegisterResponse(
            user_id=saved_user.user_id,
            name=saved_user.name,
            email=saved_user.email,
            message="Usuario registrado exitosamente"
        )
