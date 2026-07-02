"""Tests unitarios para dependencias de autenticación (hallazgo M3)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException

from presentation.dependencies import auth_deps
from shared.exceptions.application import ExternalServiceError
from shared.exceptions.base import UnauthorizedError
from shared.exceptions.domain import UserInactiveError


def _request() -> SimpleNamespace:
    """Request mínimo con .state, suficiente para las dependencias de auth."""
    return SimpleNamespace(state=SimpleNamespace())


def _response(status_code: int, json_data: dict | None = None) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json=json_data or {},
        request=httpx.Request("GET", "https://auth0.test/userinfo"),
    )


class TestGetUserInfo:
    def test_returns_payload_on_success(self, monkeypatch):
        monkeypatch.setattr(
            httpx, "get", lambda *a, **k: _response(200, {"sub": "auth0|123"})
        )

        assert auth_deps.get_user_info("token")["sub"] == "auth0|123"

    def test_raises_external_service_error_on_http_error_status(self, monkeypatch):
        """Regresión M3: un status != 200 debe fallar, no devolver None."""
        monkeypatch.setattr(httpx, "get", lambda *a, **k: _response(401))

        with pytest.raises(ExternalServiceError):
            auth_deps.get_user_info("token")

    def test_raises_external_service_error_on_network_error(self, monkeypatch):
        def _network_error(*a, **k):
            raise httpx.ConnectError("connection refused")

        monkeypatch.setattr(httpx, "get", _network_error)

        with pytest.raises(ExternalServiceError):
            auth_deps.get_user_info("token")


@pytest.mark.asyncio
class TestGetUserDualAuth:
    async def test_missing_credentials_raises_unauthorized(self):
        with pytest.raises(UnauthorizedError):
            await auth_deps.get_user_dual_auth(
                request=_request(),
                api_key=None,
                credentials=None,
                service=AsyncMock(),
                db=None,
            )

    async def test_api_key_path_sets_state_and_returns_user(self):
        user = SimpleNamespace(id=1, is_active=True)
        service = AsyncMock()
        service.authenticate.return_value = (user, ["transactions:read"])
        request = _request()

        result = await auth_deps.get_user_dual_auth(
            request=request,
            api_key="moon_test_key",
            credentials=None,
            service=service,
            db=None,
        )

        assert result is user
        assert request.state.auth_method == "api_key"
        assert request.state.api_key_scopes == ["transactions:read"]
        service.authenticate.assert_awaited_once_with("moon_test_key")

    async def test_jwt_path_sets_state_and_returns_user(self, monkeypatch):
        user = SimpleNamespace(id=1, is_active=True)
        monkeypatch.setattr(
            auth_deps,
            "get_current_active_user_from_url_token",
            AsyncMock(return_value=user),
        )
        request = _request()

        result = await auth_deps.get_user_dual_auth(
            request=request,
            api_key=None,
            credentials=SimpleNamespace(credentials="jwt-token"),
            service=AsyncMock(),
            db=None,
        )

        assert result is user
        assert request.state.auth_method == "jwt"

    async def test_jwt_path_inactive_user_raises(self, monkeypatch):
        user = SimpleNamespace(id=1, is_active=False)
        monkeypatch.setattr(
            auth_deps,
            "get_current_active_user_from_url_token",
            AsyncMock(return_value=user),
        )

        with pytest.raises(UserInactiveError):
            await auth_deps.get_user_dual_auth(
                request=_request(),
                api_key=None,
                credentials=SimpleNamespace(credentials="jwt-token"),
                service=AsyncMock(),
                db=None,
            )


@pytest.mark.asyncio
class TestRequireScope:
    async def test_jwt_auth_bypasses_scope_check(self):
        checker = auth_deps.require_scope("transactions:write")
        request = _request()
        request.state.auth_method = "jwt"
        user = SimpleNamespace(id=1)

        assert await checker(request, user=user) is user

    async def test_api_key_with_scope_is_allowed(self):
        checker = auth_deps.require_scope("transactions:read")
        request = _request()
        request.state.auth_method = "api_key"
        request.state.api_key_scopes = ["transactions:read"]
        user = SimpleNamespace(id=1)

        assert await checker(request, user=user) is user

    async def test_api_key_missing_scope_raises_403(self):
        checker = auth_deps.require_scope("transactions:write")
        request = _request()
        request.state.auth_method = "api_key"
        request.state.api_key_scopes = ["transactions:read"]

        with pytest.raises(HTTPException) as exc_info:
            await checker(request, user=SimpleNamespace(id=1))

        assert exc_info.value.status_code == 403
        assert "transactions:write" in exc_info.value.detail
