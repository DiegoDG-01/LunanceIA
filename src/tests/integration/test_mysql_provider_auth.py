"""Login con Google y Apple contra MySQL 8 real (InnoDB): unicidad de `google_sub`/`apple_sub`
con collation binaria y dos altas simultáneas de la misma identidad. Arranca su propio
contenedor desechable; sin Docker, se salta.

    uv run pytest -q -m integration src/tests/integration/test_mysql_provider_auth.py
"""

import asyncio
import uuid
from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio
from fakeredis import FakeAsyncRedis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from infrastructure.cache.redis import set_redis
from infrastructure.database.connection import Base, get_db
from infrastructure.database.models.user import UserModel
from infrastructure.external_services.email.memory import InMemoryEmailSender
from main import app
from presentation.dependencies.email_deps import get_email_sender
from presentation.dependencies.identity_deps import (
    get_apple_gateway,
    get_google_verifier,
)

from ..identity_providers import NONCE, FakeApple, FakeGoogle, apple_client, google_verifier
from .test_mysql_idempotency import mysql_url  # noqa: F401  (fixture del contenedor)

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def mysql_client(mysql_url) -> AsyncIterator[httpx.AsyncClient]:  # noqa: F811
    engine = create_async_engine(mysql_url, pool_size=5, max_overflow=0)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

    async def override_get_db():
        async with sessions() as session:
            yield session

    google, apple = FakeGoogle(), FakeApple()
    google_gateway = google_verifier(google)
    apple_gateway, _ = apple_client(apple, with_key=False)
    set_redis(FakeAsyncRedis(decode_responses=True))
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_email_sender] = lambda: InMemoryEmailSender()
    app.dependency_overrides[get_google_verifier] = lambda: google_gateway
    app.dependency_overrides[get_apple_gateway] = lambda: apple_gateway
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test/api/v2"
        ) as client:
            client.google = google  # type: ignore[attr-defined]
            client.apple = apple  # type: ignore[attr-defined]
            client.sessions = sessions  # type: ignore[attr-defined]
            yield client
    finally:
        app.dependency_overrides.clear()
        set_redis(None)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await engine.dispose()


def _device() -> dict[str, str]:
    return {"X-Lunance-Device": str(uuid.uuid4()), "X-Lunance-Client": "ios/1.0.0"}


@pytest.mark.asyncio
async def test_apple_subjects_differing_only_in_case_are_different_accounts(
    mysql_client,
):
    lower = await mysql_client.post(
        "/auth/apple",
        json={
            "id_token": mysql_client.apple.identity_token(sub="000123.abcdef.0042"),
            "nonce": NONCE,
        },
        headers=_device(),
    )
    upper = await mysql_client.post(
        "/auth/apple",
        json={
            "id_token": mysql_client.apple.identity_token(sub="000123.ABCDEF.0042"),
            "nonce": NONCE,
        },
        headers=_device(),
    )

    assert lower.status_code == 200 and lower.json()["account_created"]
    assert upper.status_code == 200 and upper.json()["account_created"]


@pytest.mark.asyncio
async def test_concurrent_first_sign_ins_create_a_single_account(mysql_client):
    sub, email = "109876543210", "concurrente@gmail.com"
    tokens = [
        mysql_client.google.id_token(sub=sub, email=email, name="Concurrente")
        for _ in range(3)
    ]

    responses = await asyncio.gather(
        *(
            mysql_client.post("/auth/google", json={"id_token": t}, headers=_device())
            for t in tokens
        )
    )

    # La que pierde la carrera vuelve a intentarlo y entra en la cuenta que creó la otra.
    assert [r.status_code for r in responses] == [200, 200, 200], [
        r.text for r in responses
    ]
    assert sum(r.json()["account_created"] for r in responses) == 1
    async with mysql_client.sessions() as db:
        count = (
            await db.execute(
                select(func.count())
                .select_from(UserModel)
                .where(UserModel.google_sub == sub)
            )
        ).scalar_one()
    assert count == 1


@pytest.mark.asyncio
async def test_generated_username_avoids_case_insensitive_collisions(mysql_client):
    first = await mysql_client.post(
        "/auth/google",
        json={"id_token": mysql_client.google.id_token(name="Ana Mysql")},
        headers=_device(),
    )
    second = await mysql_client.post(
        "/auth/google",
        json={"id_token": mysql_client.google.id_token(name="ANA MYSQL")},
        headers=_device(),
    )

    assert first.status_code == 200 and second.status_code == 200
    async with mysql_client.sessions() as db:
        names = (
            await db.execute(
                select(UserModel.name).where(UserModel.name.like("anamysql%"))
            )
        ).scalars()
        assert len(set(names)) == 2
