"""E2E de la fase 3 con la autenticación real: login con Google y Apple, vinculación,
notificaciones de Apple, proveedor sin configurar y Redis caído. Google y Apple son falsos
(claves generadas aquí, `httpx.MockTransport`): no hay red."""

import uuid
from collections.abc import AsyncGenerator
from types import SimpleNamespace

import httpx
import pytest
import pytest_asyncio
from fakeredis import FakeAsyncRedis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import infrastructure.rate_limiting.limiters as limiters_mod
from infrastructure.cache.redis import set_redis
from infrastructure.database.connection import Base, get_db
from infrastructure.database.models.user import UserModel
from infrastructure.external_services.email.memory import InMemoryEmailSender
from infrastructure.security.secret_cipher import AesGcmSecretCipher
from main import app
from presentation.dependencies.auth_services import get_password_hasher
from presentation.dependencies.email_deps import get_email_sender
from presentation.dependencies.identity_deps import (
    get_apple_gateway,
    get_apple_token_cipher,
    get_google_verifier,
)
from tests.auth_helpers import BrokenRedis, fast_hasher
from tests.email_flow import PASSWORD, signup
from tests.identity_providers import (
    ENCRYPTION_SECRET,
    NONCE,
    FakeApple,
    FakeGoogle,
    apple_client,
    google_verifier,
    rsa_key,
)

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


@pytest_asyncio.fixture
async def sessionmaker() -> AsyncGenerator[async_sessionmaker, None]:
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
    """Una sesión de BD por petición, Redis falso, buzón en memoria y proveedores falsos."""

    async def override_get_db():
        async with sessionmaker() as session:
            yield session

    google, apple = FakeGoogle(), FakeApple()
    google_gateway = google_verifier(google)
    apple_gateway, _ = apple_client(apple)
    cipher = AesGcmSecretCipher(ENCRYPTION_SECRET, purpose="apple-refresh-token")
    hasher = fast_hasher()
    outbox = InMemoryEmailSender()
    set_redis(FakeAsyncRedis(decode_responses=True))
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_password_hasher] = lambda: hasher
    app.dependency_overrides[get_email_sender] = lambda: outbox
    app.dependency_overrides[get_google_verifier] = lambda: google_gateway
    app.dependency_overrides[get_apple_gateway] = lambda: apple_gateway
    app.dependency_overrides[get_apple_token_cipher] = lambda: cipher
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test/api/v2"
    ) as http:
        http.outbox = outbox  # type: ignore[attr-defined]
        http.google = google  # type: ignore[attr-defined]
        http.apple = apple  # type: ignore[attr-defined]
        http.sessions = sessionmaker  # type: ignore[attr-defined]
        yield http
    app.dependency_overrides.clear()
    set_redis(None)


def _device(platform: str = "web") -> dict[str, str]:
    headers = {"X-Lunance-Device": str(uuid.uuid4())}
    if platform != "web":
        headers["X-Lunance-Client"] = f"{platform}/1.0.0"
    return headers


async def _google(http, token: str, platform: str = "ios", **body) -> httpx.Response:
    response = await http.post(
        "/auth/google", json={"id_token": token, **body}, headers=_device(platform)
    )
    http.cookies.clear()
    return response


async def _apple(http, token: str, **body) -> httpx.Response:
    return await http.post(
        "/auth/apple",
        json={"id_token": token, "nonce": NONCE, **body},
        headers=_device("ios"),
    )


def _bearer(response: httpx.Response) -> dict[str, str]:
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _user(http, email: str) -> UserModel:
    async with http.sessions() as db:
        return (
            await db.execute(select(UserModel).where(UserModel.email == email))
        ).scalar_one()


class TestGoogleSignIn:
    async def test_web_gets_the_refresh_in_a_cookie(self, client):
        response = await client.post(
            "/auth/google",
            json={"id_token": client.google.id_token(email="ana@gmail.com")},
            headers=_device("web"),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["account_created"] is True and body["provider_linked"] is False
        assert "refresh_token" not in body
        assert "refresh_token=" in response.headers["set-cookie"]
        assert "httponly" in response.headers["set-cookie"].lower()

    async def test_mobile_gets_the_refresh_in_the_body_and_can_refresh(self, client):
        headers = _device("ios")
        response = await client.post(
            "/auth/google",
            json={"id_token": client.google.id_token(), "device_name": "iPhone"},
            headers=headers,
        )
        refreshed = await client.post(
            "/auth/refresh",
            json={"refresh_token": response.json()["refresh_token"]},
            headers=headers,
        )

        assert response.status_code == 200 and response.json()["refresh_token"]
        assert refreshed.status_code == 200

    async def test_me_lists_the_login_methods(self, client):
        auth = _bearer(await _google(client, client.google.id_token(name="Ana López")))

        me = await client.get("/auth/me", headers=auth)

        assert me.json()["login_methods"] == ["google"]
        assert me.json()["username"] == "analopez"
        assert me.json()["email_verified"] is True

    async def test_forged_token_is_rejected(self, client):
        response = await _google(client, client.google.id_token(key=rsa_key()))

        assert response.status_code == 401
        assert response.json()["error_code"] == "AUTH_INVALID_PROVIDER_TOKEN"

    async def test_replayed_token_is_rejected(self, client):
        token = client.google.id_token()
        assert (await _google(client, token)).status_code == 200

        replay = await _google(client, token)

        assert replay.status_code == 401
        assert replay.json()["error_code"] == "AUTH_INVALID_PROVIDER_TOKEN"

    async def test_existing_account_with_another_domain_must_link_from_settings(
        self, client
    ):
        email = await signup(client, client.outbox, email="ana@empresa.com")

        response = await _google(client, client.google.id_token(email=email))

        assert response.status_code == 409
        body = response.json()
        assert body["error_code"] == "AUTH_PROVIDER_LINK_REQUIRED"
        assert body["details"][0]["input"] == ["password"]
        assert "vincula" in body["message"]

    async def test_gmail_account_is_linked_and_keeps_its_password(self, client):
        email = await signup(client, client.outbox, email="ana@gmail.com")

        response = await _google(client, client.google.id_token(email=email))
        login = await client.post(
            "/auth/login",
            json={"email": email, "password": PASSWORD},
            headers=_device("ios"),
        )

        assert response.status_code == 200 and response.json()["provider_linked"]
        assert login.status_code == 200
        assert client.outbox.sent_to(email)[-1].tag == "provider-linked"

    async def test_device_header_is_required(self, client):
        response = await client.post(
            "/auth/google", json={"id_token": client.google.id_token()}
        )

        assert response.status_code == 422

    async def test_validation_errors_do_not_echo_the_token(self, client):
        response = await client.post(
            "/auth/google", json={"id_token": "x" * 9000}, headers=_device()
        )

        assert response.status_code == 422
        assert all(detail["input"] is None for detail in response.json()["details"])

    async def test_keys_unavailable_answers_503(self, client):
        client.google.keys_down = True

        response = await _google(client, client.google.id_token())

        assert response.status_code == 503
        assert response.json()["error_code"] == "AUTH_PROVIDER_UNAVAILABLE"
        assert response.headers["Retry-After"] == "5"


class TestConfigurationAndOutages:
    async def test_provider_not_configured(self, client):
        app.dependency_overrides[get_google_verifier] = lambda: None
        app.dependency_overrides[get_apple_gateway] = lambda: None

        google = await _google(client, "token")
        apple = await _apple(client, "token")
        notification = await client.post(
            "/auth/apple/notifications", json={"payload": "x"}
        )

        for response in (google, apple, notification):
            assert response.status_code == 503
            assert response.json()["error_code"] == "AUTH_PROVIDER_NOT_CONFIGURED"

    async def test_redis_down_answers_503(self, client):
        token = client.google.id_token()
        set_redis(BrokenRedis())  # type: ignore[arg-type]

        response = await _google(client, token)

        assert response.status_code == 503
        assert response.headers["Retry-After"] == "5"

    async def test_rate_limit_fails_closed(self, client, monkeypatch):
        monkeypatch.setattr(limiters_mod, "settings", SimpleNamespace(ENVIRONMENT="DEV"))
        set_redis(BrokenRedis())  # type: ignore[arg-type]

        # Con un token inválido, sin el límite respondería 401: el 503 viene del limiter.
        response = await _apple(client, "no-es-un-jwt")

        assert response.status_code == 503
        assert response.json()["error_code"] == "SERVICE_UNAVAILABLE"


class TestAppleSignIn:
    async def test_sign_in_with_code_stores_the_refresh_token_encrypted(self, client):
        token = client.apple.identity_token(email="ana@icloud.com", is_private_email=None)

        response = await _apple(
            client, token, authorization_code="code-1", name="Ana Pérez"
        )

        assert response.status_code == 200
        assert response.json()["account_created"] is True
        user = await _user(client, "ana@icloud.com")
        assert user.name == "anaperez"
        assert user.apple_refresh_token and "code-1" not in user.apple_refresh_token

    async def test_wrong_nonce_is_rejected(self, client):
        response = await client.post(
            "/auth/apple",
            json={"id_token": client.apple.identity_token(), "nonce": "otro"},
            headers=_device("ios"),
        )

        assert response.status_code == 401

    async def test_consent_revoked_notification_closes_the_sessions(self, client):
        sub = "000123.e2e.0042"
        auth = _bearer(await _apple(client, client.apple.identity_token(sub=sub)))
        assert (await client.get("/auth/sessions", headers=auth)).status_code == 200

        notified = await client.post(
            "/auth/apple/notifications",
            json={"payload": client.apple.notification("consent-revoked", sub)},
        )

        assert notified.status_code == 200
        assert (await client.get("/auth/sessions", headers=auth)).status_code == 401

    async def test_forged_notification_is_rejected(self, client):
        forged = client.apple.sign({"events": "{}"}, key=rsa_key())

        response = await client.post(
            "/auth/apple/notifications", json={"payload": forged}
        )

        assert response.status_code == 401


class TestLinkingFromSettings:
    async def _password_user(self, client, email="ana@empresa.com"):
        await signup(client, client.outbox, email=email)
        response = await client.post(
            "/auth/login",
            json={"email": email, "password": PASSWORD},
            headers=_device("ios"),
        )
        return _bearer(response)

    async def test_link_and_unlink_google(self, client):
        auth = await self._password_user(client)

        linked = await client.post(
            "/auth/providers/google",
            json={"id_token": client.google.id_token(sub="g-77", email="otra@gmail.com")},
            headers=auth,
        )
        sign_in = await _google(
            client, client.google.id_token(sub="g-77", email="otra@gmail.com")
        )
        unlinked = await client.delete("/auth/providers/google", headers=auth)

        assert linked.status_code == 200
        assert linked.json()["login_methods"] == ["password", "google"]
        assert sign_in.status_code == 200 and not sign_in.json()["account_created"]
        assert unlinked.json()["login_methods"] == ["password"]

    async def test_link_apple_with_its_code(self, client):
        auth = await self._password_user(client)

        response = await client.post(
            "/auth/providers/apple",
            json={
                "id_token": client.apple.identity_token(),
                "nonce": NONCE,
                "authorization_code": "code-5",
            },
            headers=auth,
        )

        assert response.status_code == 200
        assert (await _user(client, "ana@empresa.com")).apple_refresh_token

    async def test_google_account_of_another_user_cannot_be_linked(self, client):
        await _google(client, client.google.id_token(sub="g-taken"))
        auth = await self._password_user(client)

        response = await client.post(
            "/auth/providers/google",
            json={"id_token": client.google.id_token(sub="g-taken")},
            headers=auth,
        )

        assert response.status_code == 409
        assert response.json()["error_code"] == "AUTH_PROVIDER_IN_USE"

    async def test_last_login_method_cannot_be_removed(self, client):
        auth = _bearer(await _google(client, client.google.id_token()))

        response = await client.delete("/auth/providers/google", headers=auth)

        assert response.status_code == 409
        assert response.json()["error_code"] == "AUTH_LAST_LOGIN_METHOD"

    async def test_unknown_provider_is_a_validation_error(self, client):
        auth = _bearer(await _google(client, client.google.id_token()))

        response = await client.delete("/auth/providers/facebook", headers=auth)

        assert response.status_code == 422

    async def test_requires_a_session(self, client):
        response = await client.post(
            "/auth/providers/google", json={"id_token": client.google.id_token()}
        )

        assert response.status_code == 401


class TestAccountsWithoutPassword:
    async def test_change_password_answers_password_not_set(self, client):
        auth = _bearer(await _google(client, client.google.id_token()))

        response = await client.post(
            "/auth/password/change",
            json={"current_password": "x", "new_password": "Nueva!clave2026"},
            headers=auth,
        )

        assert response.status_code == 409
        assert response.json()["error_code"] == "AUTH_PASSWORD_NOT_SET"

    async def test_username_can_be_changed(self, client):
        auth = _bearer(await _google(client, client.google.id_token(name="Ana")))

        renamed = await client.patch("/auth/me", json={"username": "ana_nueva"}, headers=auth)

        assert renamed.status_code == 200
        assert renamed.json()["username"] == "ana_nueva"
