"""Unit tests for authentication schemas and handler edge cases (mocks)."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from application.auth.commands.login import LoginCommand, LoginHandler
from application.auth.commands.register import RegisterCommand, RegisterHandler
from application.auth.services.login_guard import LoginLocks
from domain.entities.users.user import User
from presentation.schemas.requests.auth import (
    ChangePasswordRequest,
    EmailRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
)
from shared.exceptions.domain import (
    InvalidCredentialsError,
    UsernameAlreadyExistsError,
)

from .application.auth.conftest import EMAIL_CONFIG


@pytest.mark.unit
class TestAuthSchemas:
    """Test authentication request schemas."""

    def test_register_request_valid(self):
        request = RegisterRequest(
            email="ana@example.com", username="testuser", password="Password123!"
        )
        assert request.username == "testuser"
        assert request.email == "ana@example.com"

    def test_register_request_requires_email(self):
        with pytest.raises(ValidationError):
            RegisterRequest(username="testuser", password="Password123!")  # type: ignore[call-arg]

    def test_register_request_rejects_invalid_email(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="no-es-correo", username="u", password="Password123!")

    def test_register_request_empty_username(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="ana@example.com", username="", password="Password123!")

    def test_register_request_short_password(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="ana@example.com", username="u", password="short")

    def test_register_request_caps_password_length(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="ana@example.com", username="u", password="Aa1!" + "x" * 300
            )

    def test_login_request_valid(self):
        request = LoginRequest(email="ana@example.com", password="Password123!")
        assert request.email == "ana@example.com"
        assert request.password == "Password123!"

    def test_login_request_requires_email_not_username(self):
        with pytest.raises(ValidationError):
            LoginRequest(username="testuser", password="Password123!")  # type: ignore[call-arg]

    def test_login_request_short_password(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="ana@example.com", password="short")

    def test_email_request_and_reset_and_change(self):
        assert EmailRequest(email="ana@example.com").email == "ana@example.com"
        with pytest.raises(ValidationError):
            ResetPasswordRequest(token="", password="Password123!")
        with pytest.raises(ValidationError):
            ChangePasswordRequest(current_password="", new_password="Password123!")


def _uow() -> MagicMock:
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.commit = AsyncMock()
    uow.rollback = AsyncMock()
    return uow


@pytest.mark.unit
class TestLoginHandlerEnumeration:
    """Regresión M4: no filtrar existencia de usuarios por status code/excepción."""

    def _handler(self, user):
        user_repo = MagicMock()
        user_repo.get_by_email = AsyncMock(return_value=user)
        hasher = MagicMock()
        # Sólo debe llamarse para usuarios con contraseña local válida.
        hasher.verify = AsyncMock(return_value=False)
        hasher.verify_dummy = AsyncMock()
        events = MagicMock()
        events.record = AsyncMock()
        guard = MagicMock()
        guard.locks = AsyncMock(return_value=LoginLocks(ip=None, account=None))
        guard.record_failure = AsyncMock()
        pending = MagicMock()
        pending.get_by_email = AsyncMock(return_value=None)
        self.hasher = hasher
        self.guard = guard
        return LoginHandler(
            user_repository=user_repo,
            auth_event_repository=events,
            session_manager=MagicMock(),
            password_hasher=hasher,
            revocations=MagicMock(),
            uow=_uow(),
            login_guard=guard,
            session_repository=MagicMock(),
            pending_signup_repository=pending,
        )

    @pytest.mark.asyncio
    async def test_unknown_user_raises_invalid_credentials(self):
        handler = self._handler(user=None)

        with pytest.raises(InvalidCredentialsError):
            await handler.handle(
                LoginCommand(email="ghost@example.com", password="Whatever1!")
            )

        # Mismo coste que una contraseña real: el tiempo no revela si existe.
        self.hasher.verify_dummy.assert_awaited_once()
        # Y cuenta como intento fallido igual que una contraseña incorrecta.
        self.guard.record_failure.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_user_without_local_password_raises_invalid_credentials(self):
        """Usuario sin contraseña local no debe provocar 500 ni un error distinto."""
        passwordless = User(
            id=1,
            uuid="u-1",
            name="social",
            email="a@b.com",
            password=None,
            is_active=True,
        )
        handler = self._handler(user=passwordless)

        with pytest.raises(InvalidCredentialsError):
            await handler.handle(LoginCommand(email="a@b.com", password="Whatever1!"))

        # Nunca se intenta verificar contra una contraseña inexistente.
        self.hasher.verify.assert_not_called()


@pytest.mark.unit
class TestRegisterHandlerRace:
    """Regresión M5: la carrera check-then-create no termina en 500."""

    def _handler(self, *, add_side_effect, holder=None):
        user_repo = MagicMock()
        user_repo.get_by_username = AsyncMock(return_value=None)
        user_repo.get_by_email = AsyncMock(return_value=None)
        pending = MagicMock()
        pending.get_by_email = AsyncMock(return_value=None)
        # Antes del insert nadie reserva el username; después de la carrera, `holder`.
        pending.get_by_username = AsyncMock(side_effect=[None, None, holder])
        pending.add = AsyncMock(side_effect=add_side_effect)
        hasher = MagicMock()
        hasher.hash = AsyncMock(return_value="hashed")
        self.queue = MagicMock()
        return RegisterHandler(
            user_repository=user_repo,
            pending_signup_repository=pending,
            auth_event_repository=MagicMock(),
            password_hasher=hasher,
            email_queue=self.queue,
            config=EMAIL_CONFIG,
            uow=_uow(),
        )

    @pytest.mark.asyncio
    async def test_concurrent_insert_of_same_username_raises_username_exists(self):
        from datetime import UTC, datetime, timedelta

        from domain.entities.auth.pending_signup import PendingSignup

        holder = PendingSignup(
            id=7,
            email="otra@example.com",
            username="taken",
            password_hash="h",
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        integrity_error = IntegrityError("INSERT", {}, Exception("Duplicate entry"))
        handler = self._handler(add_side_effect=integrity_error, holder=holder)

        with pytest.raises(UsernameAlreadyExistsError):
            await handler.handle(
                RegisterCommand(
                    email="ana@example.com", username="taken", password="Password123!"
                )
            )
        self.queue.enqueue.assert_not_called()

    @pytest.mark.asyncio
    async def test_concurrent_insert_of_same_email_is_silent(self):
        integrity_error = IntegrityError("INSERT", {}, Exception("Duplicate entry"))
        handler = self._handler(add_side_effect=integrity_error, holder=None)

        # El otro envío del mismo formulario ya manda el enlace.
        await handler.handle(
            RegisterCommand(
                email="ana@example.com", username="ana", password="Password123!"
            )
        )
        self.queue.enqueue.assert_not_called()
