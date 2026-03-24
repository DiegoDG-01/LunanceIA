import pytest
from unittest.mock import MagicMock, AsyncMock

from application.auth.commands.logout import LogoutCommand, LogoutHandler, LogoutResponse
from domain.entities.user import User
from shared.exceptions.application import CommandValidationError


@pytest.mark.unit
class TestLogoutHandler:
    @pytest.fixture
    def mock_user_repo(self):
        return MagicMock()

    @pytest.fixture
    def mock_auth_token_repo(self):
        return MagicMock()

    @pytest.fixture
    def mock_jwt_service(self):
        service = MagicMock()
        service.verify_refresh_token = AsyncMock(return_value="user-uuid-123")
        service.hash_refresh_token = MagicMock(return_value="hashed-refresh-token")
        return service

    @pytest.fixture
    def mock_uow(self):
        uow = AsyncMock()
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=False)
        return uow

    @pytest.fixture
    def handler(self, mock_user_repo, mock_auth_token_repo, mock_jwt_service, mock_uow):
        return LogoutHandler(
            user_repository=mock_user_repo,
            auth_token_repository=mock_auth_token_repo,
            jwt_service=mock_jwt_service,
            uow=mock_uow,
        )

    @pytest.fixture
    def mock_user(self):
        return User(
            id=1, uuid="user-uuid-123", name="testuser", password="hashed", is_active=True
        )

    @pytest.mark.asyncio
    async def test_logout_success(
        self, handler, mock_user_repo, mock_auth_token_repo, mock_user
    ):
        mock_user_repo.get_by_uuid = AsyncMock(return_value=mock_user)
        mock_auth_token_repo.revoke_refresh_token = AsyncMock(return_value=True)

        command = LogoutCommand(refresh_token="valid-refresh-token")
        result = await handler.handle(command)

        assert isinstance(result, LogoutResponse)
        assert result.message == "Logout exitoso"
        mock_auth_token_repo.revoke_refresh_token.assert_called_once_with(
            1, "hashed-refresh-token"
        )

    @pytest.mark.asyncio
    async def test_logout_empty_token_raises(self, handler):
        command = LogoutCommand(refresh_token="")

        with pytest.raises(CommandValidationError):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_logout_invalid_token_returns_success(
        self, handler, mock_jwt_service
    ):
        mock_jwt_service.verify_refresh_token = AsyncMock(return_value=None)

        command = LogoutCommand(refresh_token="invalid-token")
        result = await handler.handle(command)

        assert isinstance(result, LogoutResponse)

    @pytest.mark.asyncio
    async def test_logout_user_not_found_returns_success(
        self, handler, mock_user_repo
    ):
        mock_user_repo.get_by_uuid = AsyncMock(return_value=None)

        command = LogoutCommand(refresh_token="valid-refresh-token")
        result = await handler.handle(command)

        assert isinstance(result, LogoutResponse)

    @pytest.mark.asyncio
    async def test_logout_commits_uow(
        self, handler, mock_user_repo, mock_auth_token_repo, mock_uow, mock_user
    ):
        mock_user_repo.get_by_uuid = AsyncMock(return_value=mock_user)
        mock_auth_token_repo.revoke_refresh_token = AsyncMock(return_value=True)

        command = LogoutCommand(refresh_token="valid-refresh-token")
        await handler.handle(command)

        mock_uow.commit.assert_called_once()
