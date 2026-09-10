"""Unit tests for authentication schemas."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from sqlalchemy.exc import IntegrityError

from application.auth.commands.login import LoginCommand, LoginHandler
from application.auth.commands.register import RegisterCommand, RegisterHandler
from domain.entities.user import User
from presentation.schemas.requests.auth import (
    LoginRequest,
    RegisterRequest,
)
from shared.exceptions.domain import (
    InvalidCredentialsError,
    UsernameAlreadyExistsError,
)


@pytest.mark.unit
class TestAuthSchemas:
    """Test authentication request schemas."""

    def test_register_request_valid(self):
        request = RegisterRequest(username="testuser", password="Password123!")
        assert request.username == "testuser"
        assert request.password == "Password123!"

    def test_register_request_empty_username(self):
        with pytest.raises(ValidationError):
            RegisterRequest(username="", password="Password123!")

    def test_register_request_short_password(self):
        with pytest.raises(ValidationError):
            RegisterRequest(username="testuser", password="short")

    def test_login_request_valid(self):
        request = LoginRequest(username="testuser", password="Password123!")
        assert request.username == "testuser"
        assert request.password == "Password123!"

    def test_login_request_empty_username(self):
        with pytest.raises(ValidationError):
            LoginRequest(username="", password="Password123!")

    def test_login_request_short_password(self):
        with pytest.raises(ValidationError):
            LoginRequest(username="testuser", password="short")


@pytest.mark.unit
class TestLoginHandlerEnumeration:
    """Regresión M4: no filtrar existencia de usuarios por status code/excepción."""

    def _handler(self, user):
        user_repo = MagicMock()
        user_repo.get_by_username = AsyncMock(return_value=user)
        jwt_service = MagicMock()
        # Sólo debe llamarse para usuarios con contraseña local válida.
        jwt_service.check_password = MagicMock(return_value=False)
        return LoginHandler(
            user_repo=user_repo,
            auth_token_repo=MagicMock(),
            jwt_service=jwt_service,
            uow=MagicMock(),
            auth_config=MagicMock(),
        )

    @pytest.mark.asyncio
    async def test_unknown_user_raises_invalid_credentials(self):
        handler = self._handler(user=None)

        with pytest.raises(InvalidCredentialsError):
            await handler.handle(LoginCommand(username="ghost", password="Whatever1!"))

    @pytest.mark.asyncio
    async def test_auth0_user_without_local_password_raises_invalid_credentials(self):
        """Usuario Auth0 (password=None) no debe provocar 500 ni un error distinto."""
        auth0_user = User(
            id=1,
            uuid="u-1",
            auth0_id="auth0|abc",
            name="auth0user",
            email="a@b.com",
            password=None,
            is_active=True,
        )
        handler = self._handler(user=auth0_user)

        with pytest.raises(InvalidCredentialsError):
            await handler.handle(
                LoginCommand(username="auth0user", password="Whatever1!")
            )

        # Nunca se intenta verificar contra una contraseña inexistente.
        handler.jwt_service.check_password.assert_not_called()


@pytest.mark.unit
class TestRegisterHandlerRace:
    """Regresión M5: la carrera check-then-create se traduce a 409, no a 500."""

    def _handler(self, create_side_effect):
        user_repo = MagicMock()
        user_repo.get_by_username = AsyncMock(return_value=None)
        user_repo.create = AsyncMock(side_effect=create_side_effect)

        jwt_service = MagicMock()
        jwt_service.get_password_hash = MagicMock(return_value="hashed")

        uow = MagicMock()
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=False)
        uow.commit = AsyncMock()

        return RegisterHandler(
            user_repository=user_repo,
            jwt_service=jwt_service,
            uow=uow,
        )

    @pytest.mark.asyncio
    async def test_concurrent_insert_raises_username_exists(self):
        integrity_error = IntegrityError("INSERT", {}, Exception("Duplicate entry"))
        handler = self._handler(create_side_effect=integrity_error)

        with pytest.raises(UsernameAlreadyExistsError):
            await handler.handle(
                RegisterCommand(username="taken", password="Password123!")
            )

    @pytest.mark.asyncio
    async def test_successful_registration_commits(self):
        saved = User(id=1, uuid="u-1", name="newuser", password="hashed", is_active=True)
        handler = self._handler(create_side_effect=None)
        handler.user_repository.create = AsyncMock(return_value=saved)

        result = await handler.handle(
            RegisterCommand(username="newuser", password="Password123!")
        )

        assert result.user_uuid == "u-1"
        handler.uow.commit.assert_awaited_once()
