"""Idempotency-Key con peticiones simultáneas contra MySQL 8 real (InnoDB).

Arranca un contenedor `mysql:8.0` desechable con Docker (datos en tmpfs) y lo para al
terminar. Si Docker no está disponible, se salta. No usa MYSQL_TEST_DATABASE_URL a
propósito: el test crea y borra todas las tablas del esquema.

    uv run pytest -q -m integration src/tests/integration/test_mysql_idempotency.py
"""

import asyncio
import shutil
import subprocess
import time
from uuid import uuid4

import pymysql
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine

from application.transactions.commands.create_transaction import (
    CreateTransactionHandler,
)
from infrastructure.database.models.idempotency_key import IdempotencyKeyModel
from infrastructure.database.models.transaction import TransactionModel

from ..idempotency import with_idempotency_key
from ..isolated_app import bearer, isolated_app

pytestmark = pytest.mark.integration

MYSQL_IMAGE = "mysql:8.0"
MYSQL_PASSWORD = "lunance-test"
MYSQL_DATABASE = "lunance_idempotency_test"


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        info = subprocess.run(["docker", "info"], capture_output=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return info.returncode == 0


def _wait_for_mysql(port: int, timeout: float = 120.0) -> None:
    deadline = time.monotonic() + timeout
    while True:
        try:
            pymysql.connect(
                host="127.0.0.1",
                port=port,
                user="root",
                password=MYSQL_PASSWORD,
                database=MYSQL_DATABASE,
                connect_timeout=2,
            ).close()
            return
        except pymysql.MySQLError:
            if time.monotonic() > deadline:
                raise
            time.sleep(1)


@pytest.fixture(scope="module")
def mysql_url():
    if not _docker_available():
        pytest.skip("Docker no está disponible para levantar MySQL 8")
    container = subprocess.run(
        [
            "docker", "run", "--rm", "-d",
            "-p", "127.0.0.1::3306",
            "-e", f"MYSQL_ROOT_PASSWORD={MYSQL_PASSWORD}",
            "-e", f"MYSQL_DATABASE={MYSQL_DATABASE}",
            "--tmpfs", "/var/lib/mysql",
            MYSQL_IMAGE,
        ],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    try:
        mapping = subprocess.run(
            ["docker", "port", container, "3306/tcp"],
            capture_output=True, text=True, check=True,
        ).stdout.split()[0]
        port = int(mapping.rsplit(":", 1)[1])
        _wait_for_mysql(port)
        yield f"mysql+aiomysql://root:{MYSQL_PASSWORD}@127.0.0.1:{port}/{MYSQL_DATABASE}"
    finally:
        subprocess.run(["docker", "stop", container], capture_output=True)


@pytest_asyncio.fixture
async def api(mysql_url):
    engine = create_async_engine(mysql_url, pool_size=5, max_overflow=0)
    try:
        async with isolated_app(engine, wait_timeout=2.0) as harness:
            yield harness
    finally:
        await engine.dispose()


async def _account(api) -> str:
    response = await api.client.post(
        "/account",
        json={
            "name": "MySQL",
            "account_type": "CHECKING",
            "bank_id": 1,
            "initial_balance": 1000,
            "currency": "MXN",
        },
        headers=with_idempotency_key(bearer()),
    )
    assert response.status_code == 201, response.text
    return response.json()["account_uuid"]


def _expense(account_uuid: str) -> dict:
    return {
        "account_uuid": account_uuid,
        "category_id": 1,
        "transaction_type": "EXPENSE",
        "amount": 100,
        "description": "Concurrente",
        "transaction_date": "2026-11-01",
    }


def _slow_handler(monkeypatch, *, fail_first: bool = False):
    """Hace que el handler tarde para que la segunda petición llegue a mitad de la primera."""
    original = CreateTransactionHandler.handle
    calls: list[int] = []
    entered = asyncio.Event()

    async def slow(self, command):
        calls.append(1)
        entered.set()
        await asyncio.sleep(0.5)
        if fail_first and len(calls) == 1:
            raise RuntimeError("primer intento falla")
        return await original(self, command)

    monkeypatch.setattr(CreateTransactionHandler, "handle", slow)
    return calls, entered


@pytest.mark.asyncio
async def test_concurrent_retry_waits_and_gets_the_same_response(api, monkeypatch):
    account_uuid = await _account(api)
    calls, entered = _slow_handler(monkeypatch)
    key = str(uuid4())
    body = _expense(account_uuid)

    async def post():
        started = time.monotonic()
        response = await api.client.post(
            "/transaction/", json=body, headers=with_idempotency_key(bearer(), key)
        )
        return response, time.monotonic() - started

    first = asyncio.create_task(post())
    # La primera ya reservó la clave (la reserva va antes del handler) y la tiene
    # bloqueada sin confirmar mientras el handler duerme.
    await entered.wait()
    second = asyncio.create_task(post())
    (r1, _), (r2, waited) = await asyncio.gather(first, second)

    assert r1.status_code == r2.status_code == 200, (r1.text, r2.text)
    # Mismo JSON; MySQL reordena las claves de una columna JSON al guardarla.
    assert r2.json() == r1.json()
    assert "idempotent-replayed" not in r1.headers
    assert r2.headers["idempotent-replayed"] == "true"
    # El handler corrió una sola vez y la segunda esperó al bloqueo de la primera.
    assert len(calls) == 1
    assert waited >= 0.3
    assert await api.count(TransactionModel) == 1
    assert await api.count(IdempotencyKeyModel, IdempotencyKeyModel.key == key) == 1


@pytest.mark.asyncio
async def test_concurrent_retry_executes_if_the_first_fails(api, monkeypatch):
    account_uuid = await _account(api)
    calls, entered = _slow_handler(monkeypatch, fail_first=True)
    key = str(uuid4())
    body = _expense(account_uuid)

    async def post():
        return await api.client.post(
            "/transaction/", json=body, headers=with_idempotency_key(bearer(), key)
        )

    first = asyncio.create_task(post())
    await entered.wait()
    second = asyncio.create_task(post())
    r1, r2 = await asyncio.gather(first, second)

    # La primera hizo rollback (sin rastro de la clave), así que el INSERT de la
    # segunda entró y la segunda ejecutó la operación.
    assert r1.status_code == 500
    assert r2.status_code == 200, r2.text
    assert "idempotent-replayed" not in r2.headers
    assert len(calls) == 2
    assert await api.count(TransactionModel) == 1


@pytest.mark.asyncio
async def test_replay_and_per_user_keys_on_mysql(api):
    account_uuid = await _account(api)
    key = str(uuid4())
    body = _expense(account_uuid)

    first = await api.client.post(
        "/transaction/", json=body, headers=with_idempotency_key(bearer(), key)
    )
    retry = await api.client.post(
        "/transaction/", json=body, headers=with_idempotency_key(bearer(), key)
    )
    other_user = await api.client.post(
        "/account",
        json={
            "name": "Otro",
            "account_type": "CASH",
            "bank_id": 1,
            "initial_balance": 0,
            "currency": "MXN",
        },
        headers=with_idempotency_key(bearer(2), key),
    )

    assert first.status_code == 200, first.text
    assert retry.json() == first.json()
    assert other_user.status_code == 201, other_user.text
    assert await api.count(TransactionModel) == 1
