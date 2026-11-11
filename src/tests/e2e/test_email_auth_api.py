"""E2E de la fase 2 con la autenticación real: registro con verificación de correo,
anti-enumeración, recuperación y cambio de contraseña, throttle del login por correo y
Redis caído (503)."""

import uuid
from collections.abc import AsyncGenerator
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace

import httpx
import pytest
import pytest_asyncio
from fakeredis import FakeAsyncRedis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import infrastructure.rate_limiting.limiters as limiters_mod
from application.interfaces.email import EmailDeliveryError, EmailSender
from infrastructure.cache.login_throttle import RedisLoginThrottle
from infrastructure.cache.redis import set_redis
from infrastructure.database.connection import Base, get_db
from infrastructure.database.models.auth_event import AuthEventModel
from infrastructure.database.models.pending_signup import PendingSignupModel
from infrastructure.database.models.user import UserModel
from infrastructure.external_services.email.memory import InMemoryEmailSender
from main import app
from presentation.dependencies.auth_services import (
    get_email_auth_config,
    get_password_hasher,
)
from presentation.dependencies.email_deps import get_email_sender
from tests.auth_helpers import BrokenRedis, fast_hasher
from tests.email_flow import (
    PASSWORD,
    last_email_to,
    signup,
    token_from,
    unique_email,
)

NEW_PASSWORD = "Nueva!clave2026"

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
    """Una sesión de BD por petición (como en producción), Redis falso y buzón en memoria."""

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
        http.outbox = outbox  # type: ignore[attr-defined]
        http.redis = redis  # type: ignore[attr-defined]
        yield http
    app.dependency_overrides.clear()
    set_redis(None)


@pytest.fixture
def rate_limits_on(monkeypatch):
    """`enforce_rate_limit` no hace nada con ENVIRONMENT=TEST: aquí sí cuenta."""
    monkeypatch.setattr(limiters_mod, "settings", SimpleNamespace(ENVIRONMENT="DEV"))


def _device(platform: str = "web") -> dict[str, str]:
    headers = {"X-Lunance-Device": str(uuid.uuid4())}
    if platform != "web":
        headers["X-Lunance-Client"] = f"{platform}/1.0.0"
    return headers


async def _login(
    http: httpx.AsyncClient,
    email: str,
    password: str = PASSWORD,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    response = await http.post(
        "/auth/login",
        json={"email": email, "password": password},
        headers=headers or _device("ios"),
    )
    http.cookies.clear()
    return response


async def _bearer(http: httpx.AsyncClient, email: str, password: str = PASSWORD):
    response = await _login(http, email, password)
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _count(sessionmaker, model) -> int:
    async with sessionmaker() as db:
        return (await db.execute(select(func.count()).select_from(model))).scalar_one()


class TestSignup:
    async def test_full_flow_register_verify_login(self, client):
        email = unique_email("Ana").upper()

        register = await client.post(
            "/auth/register",
            json={"email": f"  {email} ", "username": "ana_e2e", "password": PASSWORD},
        )
        assert register.status_code == 202
        mail = last_email_to(client.outbox, email.lower())
        assert mail.html and "verify-email?token=" in mail.text
        verify = await client.post(
            "/auth/email/verify", json={"token": token_from(mail)}
        )
        assert verify.status_code == 200
        assert verify.json()["email"] == email.lower()

        headers = await _bearer(client, email.lower())
        me = (await client.get("/auth/me", headers=headers)).json()
        assert me["email"] == email.lower() and me["email_verified"] is True
        assert me["username"] == "ana_e2e"

    async def test_existing_email_gets_the_same_response_and_a_notice(
        self, client, sessionmaker
    ):
        email = await signup(client, client.outbox)
        fresh = unique_email("fresh")

        existing = await client.post(
            "/auth/register",
            json={"email": email, "username": "otro_user", "password": PASSWORD},
        )
        new = await client.post(
            "/auth/register",
            json={"email": fresh, "username": "fresh_user", "password": PASSWORD},
        )

        assert existing.status_code == new.status_code == 202
        assert existing.json() == new.json()
        assert last_email_to(client.outbox, email).tag == "signup-existing-account"
        assert last_email_to(client.outbox, fresh).tag == "verify-email"
        # Solo el correo nuevo deja un registro pendiente.
        assert await _count(sessionmaker, PendingSignupModel) == 1

    async def test_verification_link_is_single_use(self, client, sessionmaker):
        email = unique_email()
        await client.post(
            "/auth/register",
            json={"email": email, "username": "once_user", "password": PASSWORD},
        )
        token = token_from(last_email_to(client.outbox, email))

        first = await client.post("/auth/email/verify", json={"token": token})
        again = await client.post("/auth/email/verify", json={"token": token})

        assert first.status_code == 200
        assert again.status_code == 400
        assert again.json()["error_code"] == "AUTH_INVALID_TOKEN"
        assert await _count(sessionmaker, UserModel) == 1

    async def test_expired_verification_link(self, client):
        config = get_email_auth_config()
        app.dependency_overrides[get_email_auth_config] = lambda: replace(
            config, email_verification_ttl=timedelta(seconds=-1)
        )
        email = unique_email()
        await client.post(
            "/auth/register",
            json={"email": email, "username": "late_user", "password": PASSWORD},
        )

        response = await client.post(
            "/auth/email/verify",
            json={"token": token_from(last_email_to(client.outbox, email))},
        )

        assert response.status_code == 400
        assert response.json()["error_code"] == "AUTH_INVALID_TOKEN"

    async def test_resend_responds_the_same_whatever_the_email(self, client):
        account = await signup(client, client.outbox)
        pending = unique_email("pending")
        await client.post(
            "/auth/register",
            json={"email": pending, "username": "pending_u", "password": PASSWORD},
        )
        client.outbox.clear()

        responses = [
            await client.post("/auth/email/verify/resend", json={"email": email})
            for email in (account, pending, unique_email("ghost"))
        ]

        assert {r.status_code for r in responses} == {202}
        assert len({r.text for r in responses}) == 1
        # Solo el registro pendiente recibe el enlace nuevo.
        assert [m.to for m in client.outbox.outbox] == [[pending]]

    async def test_email_failure_does_not_break_the_response(self, client):
        class FailingSender(EmailSender):
            name = "failing"

            async def send(self, email):
                raise EmailDeliveryError(self.name, "HTTP 500")

        app.dependency_overrides[get_email_sender] = lambda: FailingSender()

        response = await client.post(
            "/auth/register",
            json={"email": unique_email(), "username": "fail_u", "password": PASSWORD},
        )

        assert response.status_code == 202


class TestPasswordRecovery:
    async def test_forgot_is_always_204(self, client):
        email = await signup(client, client.outbox)
        client.outbox.clear()

        known = await client.post("/auth/password/forgot", json={"email": email})
        unknown = await client.post(
            "/auth/password/forgot", json={"email": unique_email("ghost")}
        )

        assert known.status_code == unknown.status_code == 204
        assert known.content == unknown.content == b""
        assert [m.to for m in client.outbox.outbox] == [[email]]

    async def test_reset_revokes_every_session_and_changes_password(
        self, client, sessionmaker
    ):
        email = await signup(client, client.outbox)
        web, phone = await _bearer(client, email), await _bearer(client, email)
        await client.post("/auth/password/forgot", json={"email": email})
        token = token_from(last_email_to(client.outbox, email))

        response = await client.post(
            "/auth/password/reset", json={"token": token, "password": NEW_PASSWORD}
        )

        assert response.status_code == 204
        for headers in (web, phone):
            me = await client.get("/auth/me", headers=headers)
            assert me.status_code == 401
            assert me.json()["error_code"] == "AUTH_SESSION_EXPIRED"
        assert (await _login(client, email)).status_code == 401
        assert (await _login(client, email, NEW_PASSWORD)).status_code == 200
        assert last_email_to(client.outbox, email).tag == "password-changed"
        async with sessionmaker() as db:
            actions = (
                await db.execute(select(AuthEventModel.action))
            ).scalars().all()
        assert {"password.reset_requested", "password.reset"} <= set(actions)

    async def test_reset_token_cannot_be_reused(self, client):
        email = await signup(client, client.outbox)
        await client.post("/auth/password/forgot", json={"email": email})
        token = token_from(last_email_to(client.outbox, email))
        await client.post(
            "/auth/password/reset", json={"token": token, "password": NEW_PASSWORD}
        )

        again = await client.post(
            "/auth/password/reset", json={"token": token, "password": "Otra!clave99"}
        )

        assert again.status_code == 400
        assert again.json()["error_code"] == "AUTH_INVALID_TOKEN"
        assert (await _login(client, email, NEW_PASSWORD)).status_code == 200

    async def test_expired_reset_token(self, client):
        config = get_email_auth_config()
        app.dependency_overrides[get_email_auth_config] = lambda: replace(
            config, password_reset_ttl=timedelta(seconds=-1)
        )
        email = await signup(client, client.outbox)
        await client.post("/auth/password/forgot", json={"email": email})

        response = await client.post(
            "/auth/password/reset",
            json={
                "token": token_from(last_email_to(client.outbox, email)),
                "password": NEW_PASSWORD,
            },
        )

        assert response.status_code == 400
        assert (await _login(client, email)).status_code == 200


class TestChangePassword:
    async def test_keeps_this_session_and_closes_the_others(self, client):
        email = await signup(client, client.outbox)
        current, other = await _bearer(client, email), await _bearer(client, email)

        response = await client.post(
            "/auth/password/change",
            json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
            headers=current,
        )

        assert response.status_code == 204
        assert (await client.get("/auth/me", headers=current)).status_code == 200
        assert (await client.get("/auth/me", headers=other)).status_code == 401
        assert (await _login(client, email, NEW_PASSWORD)).status_code == 200

    async def test_wrong_current_password(self, client):
        email = await signup(client, client.outbox)
        headers = await _bearer(client, email)

        response = await client.post(
            "/auth/password/change",
            json={"current_password": "Wrong-pass1!", "new_password": NEW_PASSWORD},
            headers=headers,
        )

        assert response.status_code == 400
        assert response.json()["error_code"] == "AUTH_INVALID_CURRENT_PASSWORD"
        # Un error de contraseña no cierra la sesión.
        assert (await client.get("/auth/me", headers=headers)).status_code == 200

    async def test_requires_access_token(self, client):
        response = await client.post(
            "/auth/password/change",
            json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        )

        assert response.status_code == 401


class TestLoginThrottle:
    async def test_locks_email_and_ip_after_repeated_failures(self, client):
        email = await signup(client, client.outbox)
        for _ in range(RedisLoginThrottle.FREE_ATTEMPTS):
            assert (await _login(client, email, "Wrong-pass1!")).status_code == 401

        locked = await _login(client, email)

        assert locked.status_code == 429
        assert locked.json()["error_code"] == "AUTH_TOO_MANY_ATTEMPTS"
        assert 0 < int(locked.headers["Retry-After"]) <= 60

    async def test_unknown_emails_are_throttled_too(self, client):
        ghost = unique_email("ghost")
        for _ in range(RedisLoginThrottle.FREE_ATTEMPTS):
            assert (await _login(client, ghost)).status_code == 401

        assert (await _login(client, ghost)).status_code == 429

    async def test_redis_down_rejects_login_with_503(self, client):
        email = await signup(client, client.outbox)
        set_redis(BrokenRedis())  # type: ignore[arg-type]

        response = await _login(client, email)

        assert response.status_code == 503
        assert response.headers["Retry-After"] == "5"


class TestFailClosedAndMailboxLimits:
    @pytest.mark.parametrize(
        ("path", "body"),
        [
            (
                "/auth/register",
                {"email": "a@example.com", "username": "a", "password": PASSWORD},
            ),
            ("/auth/email/verify", {"token": "x"}),
            ("/auth/email/verify/resend", {"email": "a@example.com"}),
            ("/auth/password/forgot", {"email": "a@example.com"}),
            ("/auth/password/reset", {"token": "x", "password": NEW_PASSWORD}),
        ],
    )
    async def test_redis_down_is_503(self, client, rate_limits_on, path, body):
        set_redis(BrokenRedis())  # type: ignore[arg-type]

        response = await client.post(path, json=body)

        assert response.status_code == 503
        assert response.headers["Retry-After"]

    async def test_forgot_mailbox_limit_stays_silent(self, client, rate_limits_on):
        email = await signup(client, client.outbox)
        client.outbox.clear()

        responses = [
            await client.post("/auth/password/forgot", json={"email": email})
            for _ in range(4)
        ]

        assert [r.status_code for r in responses] == [204] * 4
        assert len(client.outbox.sent_to(email)) == 3

    async def test_signup_mailbox_limit_is_429(self, client, rate_limits_on):
        email = unique_email()
        await client.post(
            "/auth/register",
            json={"email": email, "username": "mailbox_u", "password": PASSWORD},
        )
        statuses = [
            (
                await client.post("/auth/email/verify/resend", json={"email": email})
            ).status_code
            for _ in range(5)
        ]

        assert statuses == [202, 202, 202, 202, 429]
        assert len(client.outbox.sent_to(email)) == 5
