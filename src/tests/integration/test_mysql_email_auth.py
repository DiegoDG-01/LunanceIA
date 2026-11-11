"""Registro, verificación y recuperación de contraseña contra MySQL 8 real (InnoDB):
locks `FOR UPDATE`, `UPDATE` condicional del canje y unicidad del username con la
collation de MySQL. Arranca su propio contenedor desechable; sin Docker, se salta.

    uv run pytest -q -m integration src/tests/integration/test_mysql_email_auth.py
"""

import asyncio
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
from presentation.dependencies.auth_services import get_password_hasher
from presentation.dependencies.email_deps import get_email_sender

from ..auth_helpers import fast_hasher
from ..email_flow import PASSWORD, last_email_to, signup, token_from, unique_email
from .test_mysql_idempotency import mysql_url  # noqa: F401  (fixture del contenedor)

pytestmark = pytest.mark.integration

NEW_PASSWORD = "Nueva!clave2026"


@pytest_asyncio.fixture
async def mysql_client(mysql_url) -> AsyncIterator[httpx.AsyncClient]:  # noqa: F811
    engine = create_async_engine(mysql_url, pool_size=5, max_overflow=0)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

    async def override_get_db():
        async with sessions() as session:
            yield session

    hasher = fast_hasher()
    outbox = InMemoryEmailSender()
    set_redis(FakeAsyncRedis(decode_responses=True))
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_password_hasher] = lambda: hasher
    app.dependency_overrides[get_email_sender] = lambda: outbox
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test/api/v2"
        ) as client:
            client.outbox = outbox  # type: ignore[attr-defined]
            client.sessions = sessions  # type: ignore[attr-defined]
            yield client
    finally:
        app.dependency_overrides.clear()
        set_redis(None)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest.mark.asyncio
async def test_concurrent_verifications_create_a_single_account(mysql_client):
    email = unique_email()
    await mysql_client.post(
        "/auth/register",
        json={"email": email, "username": "mysql_once", "password": PASSWORD},
    )
    token = token_from(last_email_to(mysql_client.outbox, email))

    responses = await asyncio.gather(
        *(
            mysql_client.post("/auth/email/verify", json={"token": token})
            for _ in range(3)
        )
    )

    assert sorted(r.status_code for r in responses) == [200, 400, 400]
    async with mysql_client.sessions() as db:
        users = (
            await db.execute(
                select(func.count()).select_from(UserModel).where(UserModel.email == email)
            )
        ).scalar_one()
    assert users == 1


@pytest.mark.asyncio
async def test_concurrent_resets_with_one_link_succeed_once(mysql_client):
    email = await signup(mysql_client, mysql_client.outbox)
    await mysql_client.post("/auth/password/forgot", json={"email": email})
    token = token_from(last_email_to(mysql_client.outbox, email))

    responses = await asyncio.gather(
        mysql_client.post(
            "/auth/password/reset", json={"token": token, "password": NEW_PASSWORD}
        ),
        mysql_client.post(
            "/auth/password/reset", json={"token": token, "password": "Otra!clave99"}
        ),
    )

    assert sorted(r.status_code for r in responses) == [204, 400]
    winner = NEW_PASSWORD if responses[0].status_code == 204 else "Otra!clave99"
    login = await mysql_client.post(
        "/auth/login",
        json={"email": email, "password": winner},
        headers={"X-Lunance-Device": "0b5f3c55-7f4e-4f0e-9a43-0d6c2d0d6b8e"},
    )
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_username_is_unique_ignoring_case(mysql_client):
    await signup(mysql_client, mysql_client.outbox, username="MysqlAna")

    response = await mysql_client.post(
        "/auth/register",
        json={"email": unique_email(), "username": "mysqlana", "password": PASSWORD},
    )

    assert response.status_code == 409
