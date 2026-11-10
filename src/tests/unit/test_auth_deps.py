"""Tests unitarios para dependencias de autenticación (hallazgo M3)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from presentation.dependencies import auth_deps
from shared.exceptions.base import UnauthorizedError
from shared.exceptions.domain import UserInactiveError


def _request(ip: str = "203.0.113.10") -> SimpleNamespace:
    """Request mínimo con .state/.client/.url, suficiente para las dependencias de auth.

    Incluye .client porque _throttle_auth_failure (M2) lee request.client.host.
    """
    return SimpleNamespace(
        state=SimpleNamespace(),
        client=SimpleNamespace(host=ip),
        url=SimpleNamespace(path="/api/v2/test"),
    )


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

    async def test_invalid_api_key_flooding_is_rate_limited_per_ip(self, monkeypatch):
        """M2: el flooding con API keys inválidas se acota por IP con 429, para
        no dejar sin límite las peticiones no autenticadas contra la capa de BD.
        """
        import infrastructure.rate_limiting.limiters as limiters_mod

        # enforce_rate_limit hace short-circuit con ENVIRONMENT=TEST; lo desactivamos
        # sustituyendo el settings del módulo (robusto ante la inmutabilidad de pydantic).
        monkeypatch.setattr(limiters_mod, "settings", SimpleNamespace(ENVIRONMENT="DEV"))
        from fakeredis import FakeAsyncRedis

        from infrastructure.cache.redis import set_redis

        set_redis(FakeAsyncRedis(decode_responses=True))

        service = AsyncMock()
        service.authenticate.side_effect = UnauthorizedError("Invalid or expired API key")
        # IP dedicada para no compartir contador con otros tests.
        request = _request(ip="198.51.100.42")

        async def _attempt():
            return await auth_deps.get_user_dual_auth(
                request=request,
                api_key="moon_bad",
                credentials=None,
                service=service,
                db=None,
            )

        blocked = False
        for _ in range(30):
            try:
                await _attempt()
            except HTTPException as exc:
                assert exc.status_code == 429
                blocked = True
                break
            except UnauthorizedError:
                continue

        assert blocked, "El flooding de API keys inválidas debe bloquearse con 429"

        # Una vez superado el umbral, la misma IP sigue bloqueada.
        with pytest.raises(HTTPException) as exc_info:
            await _attempt()
        assert exc_info.value.status_code == 429
        set_redis(None)


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
