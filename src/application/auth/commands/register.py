from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError

from application.interfaces.auth_service import PasswordHasher
from domain.entities.users.user import User
from domain.repositories.unit_of_work import AbstractUnitOfWork
from domain.repositories.users.user_repository import UserRepository
from shared.exceptions.application import CommandValidationError
from shared.exceptions.domain import UsernameAlreadyExistsError
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
        password_hasher: PasswordHasher,
        uow: AbstractUnitOfWork,
    ):
        self.user_repository = user_repository
        self.password_hasher = password_hasher
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
        password_hash = await self.password_hasher.hash(command.password)
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
