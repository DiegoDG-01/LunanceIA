import pytest
from unittest.mock import MagicMock, AsyncMock

from application.auth.commands.refresh_token import RefreshTokenCommand, RefreshTokenHandler
from application.auth.commands.login import LoginResponse
from application.interfaces.auth_service import AuthConfig
from domain.entities.user import User
from domain.entities.refresh_token import RefreshToken
from shared.exceptions.application import CommandValidationError, JWTValidationError
from datetime import datetime, timedelta


@pytest.mark.unit
class TestRefreshTokenHandler:
    @pytest.fixture
    def mock_user_repo(self):
        return MagicMock()

    @pytest.fixture
    def mock_auth_token_repo(self):
        repo = MagicMock()
        repo.save_refresh_token = AsyncMock(return_value=True)
        return repo

    @pytest.fixture
    def mock_jwt_service(self):
        service = MagicMock()
        service.verify_refresh_token = AsyncMock(return_value="user-uuid-123")
        service.hash_refresh_token = MagicMock(return_value="hashed-refresh-token")
        service.create_access_token = MagicMock(return_value="new-access-token")
        service.create_refresh_token = MagicMock(return_value="new-refresh-token")
        return service

    @pytest.fixture
    def mock_uow(self):
        uow = MagicMock()
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=False)
        uow.commit = AsyncMock()
        return uow

    @pytest.fixture
    def auth_config(self):
        return AuthConfig(
            access_token_expire_minutes=60,
            refresh_token_expire_days=7,
        )

    @pytest.fixture
    def handler(self, mock_user_repo, mock_auth_token_repo, mock_jwt_service, mock_uow, auth_config):
        return RefreshTokenHandler(
            user_repository=mock_user_repo,
            auth_token_repository=mock_auth_token_repo,
            jwt_service=mock_jwt_service,
            uow=mock_uow,
            auth_config=auth_config,
        )

    @pytest.fixture
    def mock_user(self):
        return User(
            id=1, uuid="user-uuid-123", name="testuser", password="hashed", is_active=True
        )

    @pytest.fixture
    def mock_stored_token(self):
        return RefreshToken(
            id=1,
            user_id=1,
            token_hash="hashed-refresh-token",
            is_revoked=False,
            expired_at=datetime.now() + timedelta(days=7),
        )

    @pytest.mark.asyncio
    async def test_refresh_token_success(
        self, handler, mock_user_repo, mock_auth_token_repo, mock_user, mock_stored_token
    ):
        mock_user_repo.get_by_uuid = AsyncMock(return_value=mock_user)
        mock_auth_token_repo.get_refresh_token = AsyncMock(return_value=mock_stored_token)

        command = RefreshTokenCommand(refresh_token="valid-refresh-token")
        result = await handler.handle(command)

        assert isinstance(result, LoginResponse)
        assert result.access_token == "new-access-token"
        assert result.refresh_token == "new-refresh-token"

    @pytest.mark.asyncio
    async def test_refresh_token_empty_raises(self, handler):
        command = RefreshTokenCommand(refresh_token="")

        with pytest.raises(CommandValidationError):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_refresh_token_invalid_jwt_raises(self, handler, mock_jwt_service):
        mock_jwt_service.verify_refresh_token = AsyncMock(side_effect=JWTValidationError("Invalid"))

        command = RefreshTokenCommand(refresh_token="invalid-jwt-token")

        with pytest.raises(CommandValidationError):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_refresh_token_user_not_found_raises(self, handler, mock_user_repo):
        mock_user_repo.get_by_uuid = AsyncMock(return_value=None)

        command = RefreshTokenCommand(refresh_token="valid-refresh-token")

        with pytest.raises(CommandValidationError):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_refresh_token_inactive_user_raises(self, handler, mock_user_repo):
        inactive_user = User(
            id=1, uuid="user-uuid-123", name="testuser", password="hashed", is_active=False
        )
        mock_user_repo.get_by_uuid = AsyncMock(return_value=inactive_user)

        command = RefreshTokenCommand(refresh_token="valid-refresh-token")

        with pytest.raises(CommandValidationError):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_refresh_token_not_stored_raises(
        self, handler, mock_user_repo, mock_auth_token_repo, mock_user
    ):
        mock_user_repo.get_by_uuid = AsyncMock(return_value=mock_user)
        mock_auth_token_repo.get_refresh_token = AsyncMock(return_value=None)

        command = RefreshTokenCommand(refresh_token="valid-refresh-token")

        with pytest.raises(CommandValidationError):
            await handler.handle(command)
