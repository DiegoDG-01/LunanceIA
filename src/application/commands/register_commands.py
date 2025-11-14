from dataclasses import dataclass

from pydantic import EmailStr

from domain.entities.user import User
from domain.repositories.user_repository import UserRepository
from infrastructure.security.jwt_service import JWTService
from shared.exceptions.domain import EmailAlreadyExistsError
from shared.exceptions.application import CommandValidationError
from shared.validators.business import UserValidator


@dataclass
class RegisterCommand:
    """Comando para registro de usuario."""

    name: str
    email: EmailStr
    password: str


@dataclass
class RegisterResponse:
    """Respuesta del comando de registro."""

    user_uuid: str
    name: str
    email: EmailStr
    message: str


class RegisterHandler:
    """Handler para registro de usuario."""

    def __init__(self, user_repository: UserRepository, jwt_service: JWTService):
        self.user_repository = user_repository
        self.jwt_service = jwt_service

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
        password_hash = self.jwt_service.get_password_hash(command.password)
        user = User.create_new(
            name=command.name.strip(),
            email=command.email,
            password_hash=password_hash,
        )

        # Guardar usuario
        saved_user = self.user_repository.create(user)

        return RegisterResponse(
            user_uuid=saved_user.uuid,
            name=saved_user.name,
            email=saved_user.email,
            message="Usuario registrado exitosamente",
        )
