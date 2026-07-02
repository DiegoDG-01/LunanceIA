from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError

from domain.entities.user import User
from domain.repositories.user_repository import UserRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from application.interfaces.auth_service import AuthTokenServiceInterface
from shared.exceptions.domain import UsernameAlreadyExistsError
from shared.exceptions.application import CommandValidationError
from shared.validators.business import UserValidator


@dataclass
class RegisterCommand:
    """Comando para registro de usuario."""

    username: str
    password: str


@dataclass
class RegisterResponse:
    """Respuesta del comando de registro."""

    user_uuid: str
    username: str
    message: str


class RegisterHandler:
    """Handler para registro de usuario."""

    def __init__(
        self,
        user_repository: UserRepository,
        jwt_service: AuthTokenServiceInterface,
        uow: AbstractUnitOfWork,
    ):
        self.user_repository = user_repository
        self.jwt_service = jwt_service
        self.uow = uow

    async def handle(self, command: RegisterCommand) -> RegisterResponse:
        """Ejecuta el comando de registro."""
        # Validar entrada
        UserValidator.validate_password(command.password)

        if not command.username or not command.username.strip():
            raise CommandValidationError("RegisterCommand", ["El nombre es requerido"])

        # Verificar que el username no exista
        existing_user = await self.user_repository.get_by_username(command.username)
        if existing_user:
            raise UsernameAlreadyExistsError()

        # Crear usuario
        password_hash = self.jwt_service.get_password_hash(command.password)
        user = User.create_local_user(name=command.username, password=password_hash)

        async with self.uow:
            try:
                saved_user = await self.user_repository.create(user)
                await self.uow.commit()
            except IntegrityError:
                raise UsernameAlreadyExistsError()

        return RegisterResponse(
            user_uuid=saved_user.uuid,
            username=saved_user.name,
            message="Usuario registrado exitosamente",
        )
