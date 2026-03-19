import pytest
from unittest.mock import MagicMock, AsyncMock

from application.auth.commands.register import RegisterCommand, RegisterHandler, RegisterResponse
from domain.entities.user import User
from shared.exceptions.domain import UsernameAlreadyExistsError
from shared.exceptions.application import CommandValidationError
from shared.exceptions.base import ValidationError


@pytest.mark.unit
class TestRegisterHandler:
    @pytest.fixture
    def mock_user_repo(self):
        return MagicMock()

    @pytest.fixture
    def mock_jwt_service(self):
        service = MagicMock()
        service.get_password_hash = MagicMock(return_value="hashed-password-123")
        return service

    @pytest.fixture
    def mock_uow(self):
        uow = AsyncMock()
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=False)
        return uow

    @pytest.fixture
    def handler(self, mock_user_repo, mock_jwt_service, mock_uow):
        return RegisterHandler(
            user_repository=mock_user_repo,
            jwt_service=mock_jwt_service,
            uow=mock_uow,
        )

    @pytest.mark.asyncio
    async def test_register_success(self, handler, mock_user_repo):
        mock_user_repo.get_by_username = AsyncMock(return_value=None)
        saved_user = User(
            id=1, uuid="new-uuid-123", name="newuser", password="hashed-password-123"
        )
        mock_user_repo.create = AsyncMock(return_value=saved_user)

        command = RegisterCommand(username="newuser", password="Password123!")
        result = await handler.handle(command)

        assert isinstance(result, RegisterResponse)
        assert result.user_uuid == "new-uuid-123"
        assert result.username == "newuser"
        assert result.message == "Usuario registrado exitosamente"

    @pytest.mark.asyncio
    async def test_register_empty_username_raises(self, handler):
        command = RegisterCommand(username="", password="Password123!")

        with pytest.raises(CommandValidationError):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_register_whitespace_username_raises(self, handler):
        command = RegisterCommand(username="   ", password="Password123!")

        with pytest.raises(CommandValidationError):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_register_duplicate_username_raises(self, handler, mock_user_repo):
        existing_user = User(id=1, uuid="u-1", name="existinguser", password="hashed")
        mock_user_repo.get_by_username = AsyncMock(return_value=existing_user)

        command = RegisterCommand(username="existinguser", password="Password123!")

        with pytest.raises(UsernameAlreadyExistsError):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_register_weak_password_raises(self, handler):
        command = RegisterCommand(username="newuser", password="weak")

        with pytest.raises(ValidationError):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_register_hashes_password(self, handler, mock_user_repo, mock_jwt_service):
        mock_user_repo.get_by_username = AsyncMock(return_value=None)
        saved_user = User(id=1, uuid="u-1", name="newuser", password="hashed-password-123")
        mock_user_repo.create = AsyncMock(return_value=saved_user)

        command = RegisterCommand(username="newuser", password="Password123!")
        await handler.handle(command)

        mock_jwt_service.get_password_hash.assert_called_once_with("Password123!")
        mock_user_repo.create.assert_called_once()
        created_user = mock_user_repo.create.call_args[0][0]
        assert created_user.password == "hashed-password-123"

    @pytest.mark.asyncio
    async def test_register_commits_uow(self, handler, mock_user_repo, mock_uow):
        mock_user_repo.get_by_username = AsyncMock(return_value=None)
        saved_user = User(id=1, uuid="u-1", name="newuser", password="hashed")
        mock_user_repo.create = AsyncMock(return_value=saved_user)

        command = RegisterCommand(username="newuser", password="Password123!")
        await handler.handle(command)

        mock_uow.commit.assert_called_once()
