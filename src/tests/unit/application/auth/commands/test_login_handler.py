import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import timedelta

from application.auth.commands.login import LoginCommand, LoginHandler, LoginResponse
from application.interfaces.auth_service import AuthConfig
from domain.entities.user import User
from shared.exceptions.application import CommandValidationError
from shared.exceptions.domain import InvalidCredentialsError, UserInactiveError


@pytest.mark.unit
class TestLoginHandler:
    @pytest.fixture
    def mock_user_repo(self):
        return MagicMock()

    @pytest.fixture
    def mock_auth_token_repo(self):
        return MagicMock()

    @pytest.fixture
    def mock_jwt_service(self):
        service = MagicMock()
        service.check_password = MagicMock(return_value=True)
        service.create_access_token = MagicMock(return_value="access-token-123")
        service.create_refresh_token = MagicMock(return_value="refresh-token-123")
        service.hash_refresh_token = MagicMock(return_value="hashed-refresh-token")
        return service

    @pytest.fixture
    def mock_uow(self):
        uow = AsyncMock()
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=False)
        return uow

    @pytest.fixture
    def auth_config(self):
        return AuthConfig(
            access_token_expire_minutes=60,
            refresh_token_expire_days=7,
        )

    @pytest.fixture
    def handler(self, mock_user_repo, mock_auth_token_repo, mock_jwt_service, mock_uow, auth_config):
        return LoginHandler(
            user_repo=mock_user_repo,
            auth_token_repo=mock_auth_token_repo,
            jwt_service=mock_jwt_service,
            uow=mock_uow,
            auth_config=auth_config,
        )

    @pytest.fixture
    def mock_user(self):
        return User(
            id=1,
            uuid="user-uuid-123",
            name="testuser",
            password="hashed-password",
            is_active=True,
        )

    @pytest.mark.asyncio
    async def test_login_success(self, handler, mock_user_repo, mock_auth_token_repo, mock_jwt_service, mock_user):
        mock_user_repo.get_by_username = AsyncMock(return_value=mock_user)
        mock_auth_token_repo.save_refresh_token = AsyncMock(return_value=True)

        command = LoginCommand(username="testuser", password="Password123!")
        result = await handler.handle(command)

        assert isinstance(result, LoginResponse)
        assert result.access_token == "access-token-123"
        assert result.refresh_token == "refresh-token-123"
        assert result.token_type == "bearer"
        mock_user_repo.get_by_username.assert_called_once_with("testuser")
        mock_jwt_service.check_password.assert_called_once_with("Password123!", "hashed-password")

    @pytest.mark.asyncio
    async def test_login_empty_username_raises(self, handler):
        command = LoginCommand(username="", password="Password123!")

        with pytest.raises(CommandValidationError):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_login_empty_password_raises(self, handler):
        command = LoginCommand(username="testuser", password="")

        with pytest.raises(CommandValidationError):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_login_user_not_found_raises(self, handler, mock_user_repo):
        mock_user_repo.get_by_username = AsyncMock(return_value=None)

        command = LoginCommand(username="nonexistent", password="Password123!")

        with pytest.raises(InvalidCredentialsError):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_login_inactive_user_raises(self, handler, mock_user_repo):
        inactive_user = User(
            id=1, uuid="u-1", name="testuser", password="hashed", is_active=False
        )
        mock_user_repo.get_by_username = AsyncMock(return_value=inactive_user)

        command = LoginCommand(username="testuser", password="Password123!")

        with pytest.raises(UserInactiveError):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_login_wrong_password_raises(self, handler, mock_user_repo, mock_jwt_service, mock_user):
        mock_user_repo.get_by_username = AsyncMock(return_value=mock_user)
        mock_jwt_service.check_password = MagicMock(return_value=False)

        command = LoginCommand(username="testuser", password="WrongPassword!")

        with pytest.raises(InvalidCredentialsError):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_login_saves_refresh_token(self, handler, mock_user_repo, mock_auth_token_repo, mock_user):
        mock_user_repo.get_by_username = AsyncMock(return_value=mock_user)
        mock_auth_token_repo.save_refresh_token = AsyncMock(return_value=True)

        command = LoginCommand(username="testuser", password="Password123!")
        await handler.handle(command)

        mock_auth_token_repo.save_refresh_token.assert_called_once()
        call_kwargs = mock_auth_token_repo.save_refresh_token.call_args
        assert call_kwargs.kwargs["user_id"] == 1
        assert call_kwargs.kwargs["refresh_hash_token"] == "hashed-refresh-token"
