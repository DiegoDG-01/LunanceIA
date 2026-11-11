"""E2E de sesiones multi-dispositivo con la autenticación real (sin mocks de usuario):
cookie en web vs body en mobile, listar y cerrar sesiones y revocación inmediata."""

import uuid
from collections.abc import AsyncGenerator
from dataclasses import replace
from datetime import timedelta

import httpx
import pytest
import pytest_asyncio
from fakeredis import FakeAsyncRedis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from infrastructure.cache.redis import set_redis
from infrastructure.database.connection import Base, get_db
from infrastructure.database.models.auth_event import AuthEventModel
from infrastructure.external_services.email.memory import InMemoryEmailSender
from main import app
from presentation.dependencies.auth_services import get_auth_config, get_password_hasher
from presentation.dependencies.email_deps import get_email_sender
from tests.auth_helpers import fast_hasher
from tests.email_flow import PASSWORD, signup

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


@pytest_asyncio.fixture
async def sessionmaker() -> AsyncGenerator[async_sessionmaker, None]:
    """Base propia y vacía por test, con commits y rollbacks reales (una sesión por petición,
    como en producción): un rollback de un handler no se lleva los datos del test."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(sessionmaker) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Cliente contra la app con la autenticación real; solo se sustituyen BD, Redis y el
    coste de Argon2."""

    async def override_get_db():
        async with sessionmaker() as session:
            yield session

    hasher = fast_hasher()
    redis = FakeAsyncRedis(decode_responses=True)
    outbox = InMemoryEmailSender()
    set_redis(redis)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_password_hasher] = lambda: hasher
    app.dependency_overrides[get_email_sender] = lambda: outbox
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test/api/v2"
    ) as http:
        http.redis = redis  # type: ignore[attr-defined]
        http.outbox = outbox  # type: ignore[attr-defined]
        yield http
    app.dependency_overrides.clear()
    set_redis(None)


class Device:
    """Un dispositivo con su id estable y su plataforma."""

    def __init__(self, platform: str = "web") -> None:
        self.id = str(uuid.uuid4())
        self.platform = platform
        self.access_token: str | None = None
        self.refresh_token: str | None = None

    @property
    def headers(self) -> dict[str, str]:
        headers = {"X-Lunance-Device": self.id}
        if self.platform != "web":
            headers["X-Lunance-Client"] = f"{self.platform}/1.0.0"
        return headers

    @property
    def auth(self) -> dict[str, str]:
        return {**self.headers, "Authorization": f"Bearer {self.access_token}"}

    def _cookies(self) -> dict[str, str]:
        if self.platform == "web" and self.refresh_token:
            return {"Cookie": f"refresh_token={self.refresh_token}"}
        return {}

    @staticmethod
    def _forget_jar(http: httpx.AsyncClient) -> None:
        # Cada dispositivo manda su cookie a mano: el jar compartido de httpx no debe
        # reenviar la de otro dispositivo.
        http.cookies.clear()

    def _store(self, response: httpx.Response) -> None:
        data = response.json()
        self.access_token = data["access_token"]
        if self.platform == "web":
            self.refresh_token = response.cookies.get("refresh_token")
        else:
            self.refresh_token = data["refresh_token"]

    async def login(self, http: httpx.AsyncClient, email: str, **extra) -> httpx.Response:
        response = await http.post(
            "/auth/login",
            json={"email": email, "password": PASSWORD, **extra},
            headers=self.headers,
        )
        self._forget_jar(http)
        if response.status_code == 200:
            self._store(response)
        return response

    async def refresh(self, http: httpx.AsyncClient) -> httpx.Response:
        body = None if self.platform == "web" else {"refresh_token": self.refresh_token}
        response = await http.post(
            "/auth/refresh", json=body, headers={**self.headers, **self._cookies()}
        )
        self._forget_jar(http)
        if response.status_code == 200:
            self._store(response)
        return response

    async def logout(self, http: httpx.AsyncClient, **body) -> httpx.Response:
        if self.platform != "web":
            body["refresh_token"] = self.refresh_token
        response = await http.post(
            "/auth/logout", json=body, headers={**self.headers, **self._cookies()}
        )
        self._forget_jar(http)
        return response


async def _register(http: httpx.AsyncClient) -> str:
    """Cuenta confirmada por correo; devuelve el correo con el que se entra."""
    return await signup(http, http.outbox)  # type: ignore[attr-defined]


class TestTransport:
    async def test_web_login_sets_httponly_cookie_and_no_body_token(self, client):
        email = await _register(client)
        web = Device("web")

        response = await web.login(client, email)

        assert response.status_code == 200
        assert "refresh_token" not in response.json()
        cookie = response.headers["set-cookie"]
        assert cookie.startswith("refresh_token=rt_")
        assert "HttpOnly" in cookie
        assert "Path=/api/v2/auth" in cookie
        assert "Max-Age=86400" in cookie  # 1 día de inactividad

    async def test_mobile_login_returns_refresh_in_body_without_cookie(self, client):
        email = await _register(client)
        phone = Device("ios")

        response = await phone.login(client, email)

        assert response.status_code == 200
        assert response.json()["refresh_token"].startswith("rt_")
        assert "set-cookie" not in response.headers

    async def test_web_refresh_reads_cookie_and_rotates_it(self, client):
        email = await _register(client)
        web = Device("web")
        await web.login(client, email)
        first = web.refresh_token

        response = await web.refresh(client)

        assert response.status_code == 200
        assert "refresh_token" not in response.json()
        assert web.refresh_token and web.refresh_token != first

    async def test_web_refresh_ignores_body_token(self, client):
        email = await _register(client)
        web = Device("web")
        await web.login(client, email)

        response = await client.post(
            "/auth/refresh",
            json={"refresh_token": web.refresh_token},
            headers=web.headers,
        )

        assert response.status_code == 401

    async def test_mobile_refresh_reads_body(self, client):
        email = await _register(client)
        phone = Device("android")
        await phone.login(client, email)
        first = phone.refresh_token

        response = await phone.refresh(client)

        assert response.status_code == 200
        assert phone.refresh_token != first
        assert "set-cookie" not in response.headers

    async def test_reusing_rotated_mobile_token_after_grace_closes_session(
        self, client
    ):
        email = await _register(client)
        phone = Device("ios")
        await phone.login(client, email)
        stolen = phone.refresh_token
        await phone.refresh(client)
        # Sin margen de gracia: cualquier reuso del token ya rotado cuenta como robo.
        config = get_auth_config()
        app.dependency_overrides[get_auth_config] = lambda: replace(
            config, refresh_reuse_grace=timedelta(seconds=-1)
        )

        reuse = await client.post(
            "/auth/refresh", json={"refresh_token": stolen}, headers=phone.headers
        )

        assert reuse.status_code == 401
        # El access token vigente de esa sesión deja de valer al instante, y también el
        # refresh legítimo: la sesión entera se cerró.
        assert (await client.get("/auth/me", headers=phone.auth)).status_code == 401
        assert (await phone.refresh(client)).status_code == 401

    @pytest.mark.parametrize(
        "headers",
        [{}, {"X-Lunance-Device": "not-a-uuid"}],
        ids=["missing", "invalid"],
    )
    async def test_login_requires_device_uuid(self, client, headers):
        email = await _register(client)

        response = await client.post(
            "/auth/login",
            json={"email": email, "password": PASSWORD},
            headers=headers,
        )

        assert response.status_code == 422

    async def test_login_rejects_unknown_platform(self, client):
        email = await _register(client)

        response = await client.post(
            "/auth/login",
            json={"email": email, "password": PASSWORD},
            headers={
                "X-Lunance-Device": str(uuid.uuid4()),
                "X-Lunance-Client": "windows/11",
            },
        )

        assert response.status_code == 422


class TestSessions:
    async def test_list_sessions_marks_current(self, client):
        email = await _register(client)
        web, phone = Device("web"), Device("ios")
        await web.login(client, email)
        await phone.login(client, email, device_name="iPhone de prueba")

        response = await client.get("/auth/sessions", headers=web.auth)

        assert response.status_code == 200
        sessions = response.json()
        assert len(sessions) == 2
        by_platform = {s["platform"]: s for s in sessions}
        assert by_platform["web"]["is_current"] is True
        assert by_platform["ios"]["is_current"] is False
        assert by_platform["ios"]["device_name"] == "iPhone de prueba"
        assert by_platform["ios"]["client"] == "ios/1.0.0"
        assert set(sessions[0]) == {
            "uuid",
            "platform",
            "device_name",
            "client",
            "created_at",
            "last_seen_at",
            "last_ip",
            "is_current",
        }

    async def test_login_again_from_same_device_replaces_its_session(self, client):
        email = await _register(client)
        web = Device("web")
        await web.login(client, email)
        old_access = web.access_token

        await web.login(client, email)

        sessions = (await client.get("/auth/sessions", headers=web.auth)).json()
        assert len(sessions) == 1
        stale = {"Authorization": f"Bearer {old_access}"}
        assert (await client.get("/auth/me", headers=stale)).status_code == 401

    async def test_close_session_from_another_device_is_immediate(self, client):
        email = await _register(client)
        web, phone = Device("web"), Device("android")
        await web.login(client, email)
        await phone.login(client, email)
        assert (await client.get("/auth/me", headers=phone.auth)).status_code == 200
        sessions = (await client.get("/auth/sessions", headers=web.auth)).json()
        phone_uuid = next(s["uuid"] for s in sessions if s["platform"] == "android")

        response = await client.delete(f"/auth/sessions/{phone_uuid}", headers=web.auth)

        assert response.status_code == 204
        me = await client.get("/auth/me", headers=phone.auth)
        assert me.status_code == 401
        assert me.json()["error_code"] == "AUTH_SESSION_EXPIRED"
        # Las rutas con autenticación dual (JWT o API key) también la rechazan.
        assert (await client.get("/account/", headers=phone.auth)).status_code == 401
        assert (await phone.refresh(client)).status_code == 401
        # La sesión que la cerró sigue funcionando.
        assert (await client.get("/auth/me", headers=web.auth)).status_code == 200
        assert (await client.get("/account/", headers=web.auth)).status_code == 200

    async def test_revocation_is_enforced_even_if_redis_lost_it(self, client):
        email = await _register(client)
        web, phone = Device("web"), Device("ios")
        await web.login(client, email)
        await phone.login(client, email)
        sessions = (await client.get("/auth/sessions", headers=web.auth)).json()
        phone_uuid = next(s["uuid"] for s in sessions if s["platform"] == "ios")
        await client.delete(f"/auth/sessions/{phone_uuid}", headers=web.auth)

        await client.redis.flushall()  # type: ignore[attr-defined]

        assert (await client.get("/auth/me", headers=phone.auth)).status_code == 401

    async def test_cannot_close_another_users_session(self, client):
        alice, bob = Device("web"), Device("web")
        await alice.login(client, await _register(client))
        await bob.login(client, await _register(client))
        bob_sessions = (await client.get("/auth/sessions", headers=bob.auth)).json()

        response = await client.delete(
            f"/auth/sessions/{bob_sessions[0]['uuid']}", headers=alice.auth
        )

        assert response.status_code == 404
        assert (await client.get("/auth/me", headers=bob.auth)).status_code == 200

    async def test_close_unknown_session_is_404(self, client):
        web = Device("web")
        await web.login(client, await _register(client))

        response = await client.delete(
            f"/auth/sessions/{uuid.uuid4()}", headers=web.auth
        )

        assert response.status_code == 404

    async def test_sessions_require_access_token(self, client):
        assert (await client.get("/auth/sessions")).status_code == 401


class TestLogout:
    async def test_web_logout_clears_cookie_and_revokes_access(self, client):
        web = Device("web")
        await web.login(client, await _register(client))

        response = await web.logout(client)

        assert response.status_code == 200
        assert 'refresh_token=""' in response.headers["set-cookie"]
        assert (await client.get("/auth/me", headers=web.auth)).status_code == 401
        assert (await web.refresh(client)).status_code == 401

    async def test_mobile_logout_with_body_token(self, client):
        phone = Device("ios")
        await phone.login(client, await _register(client))

        response = await phone.logout(client)

        assert response.status_code == 200
        assert (await client.get("/auth/me", headers=phone.auth)).status_code == 401

    async def test_logout_all_devices(self, client):
        email = await _register(client)
        web, phone, tablet = Device("web"), Device("ios"), Device("android")
        for device in (web, phone, tablet):
            await device.login(client, email)

        response = await phone.logout(client, all_devices=True)

        assert response.status_code == 200
        for device in (web, phone, tablet):
            assert (await client.get("/auth/me", headers=device.auth)).status_code == 401

    async def test_logout_only_current_device_by_default(self, client):
        email = await _register(client)
        web, phone = Device("web"), Device("ios")
        await web.login(client, email)
        await phone.login(client, email)

        await web.logout(client)

        assert (await client.get("/auth/me", headers=phone.auth)).status_code == 200


class TestAudit:
    async def test_login_events_never_store_secrets(self, client, sessionmaker):
        email = await _register(client)
        web = Device("web")
        await client.post(
            "/auth/login",
            json={"email": email, "password": "Wrong-password-1"},
            headers=web.headers,
        )
        await web.login(client, email)

        async with sessionmaker() as db:
            events = (
                await db.execute(
                    select(AuthEventModel)
                    .where(AuthEventModel.action.in_(["login.failed", "login.succeeded"]))
                    .order_by(AuthEventModel.id)
                )
            ).scalars().all()

        assert [e.action for e in events] == ["login.failed", "login.succeeded"]
        dumped = " ".join(str(e.details) for e in events)
        assert PASSWORD not in dumped and "Wrong-password-1" not in dumped
        assert web.refresh_token and web.access_token
        assert web.refresh_token not in dumped and web.access_token not in dumped
        assert (events[0].details or {})["email"] == email
        assert events[1].ip and events[1].user_agent

    async def test_throttled_login_is_audited_once_per_window(
        self, client, sessionmaker, monkeypatch
    ):
        from fastapi import HTTPException

        from presentation.api.v2.endpoints import auth as auth_endpoints

        async def _limited(*args, **kwargs):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        monkeypatch.setattr(auth_endpoints, "enforce_rate_limit", _limited)
        web = Device("web")

        for _ in range(3):
            response = await web.login(client, "Someone@Example.com")
            assert response.status_code == 429

        async with sessionmaker() as db:
            events = (
                await db.execute(
                    select(AuthEventModel).where(
                        AuthEventModel.action == "login.throttled"
                    )
                )
            ).scalars().all()
        assert len(events) == 1
        assert events[0].details == {"email": "someone@example.com", "scope": "rate_limit"}
