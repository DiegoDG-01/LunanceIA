"""E2E del header Idempotency-Key: un reintento nunca repite un movimiento de dinero.

Usa `isolated_app` (una sesión de BD por petición, commits reales sobre SQLite en un
archivo temporal) en lugar del `http_client` de conftest, que comparte una sola sesión.
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

from infrastructure.database.models.api_key import APIKeyModel
from infrastructure.database.models.idempotency_key import IdempotencyKeyModel
from infrastructure.database.models.transaction import TransactionModel
from infrastructure.database.repositories.sqlalchemy_idempotency_repository import (
    SQLAlchemyIdempotencyRepository,
)

from ..idempotency import IDEMPOTENCY_KEY_HEADER, with_idempotency_key
from ..isolated_app import IsolatedApp, bearer, isolated_app


@pytest_asyncio.fixture
async def api(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'idempotency.db'}")
    try:
        async with isolated_app(engine) as harness:
            yield harness
    finally:
        await engine.dispose()


async def _create_account(api: IsolatedApp, balance: float = 1000.0, user_id: int = 1):
    response = await api.client.post(
        "/account",
        json={
            "name": f"Cuenta {uuid4().hex[:8]}",
            "account_type": "CHECKING",
            "bank_id": 1,
            "initial_balance": balance,
            "currency": "MXN",
        },
        headers=with_idempotency_key(bearer(user_id)),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _balance(api: IsolatedApp, account_uuid: str, user_id: int = 1) -> float:
    response = await api.client.get(f"/account/{account_uuid}", headers=bearer(user_id))
    return float(response.json()["current_balance"])


def _expense(account_uuid: str, amount: float = 100.0) -> dict:
    return {
        "account_uuid": account_uuid,
        "category_id": 1,
        "transaction_type": "EXPENSE",
        "amount": amount,
        "description": "Súper",
        "transaction_date": "2026-11-01",
    }


async def _key_row(api: IsolatedApp, user_id: int, key: str):
    async with api.sessions() as session:
        return (
            await session.execute(
                select(IdempotencyKeyModel).where(
                    IdempotencyKeyModel.user_id == user_id,
                    IdempotencyKeyModel.key == key,
                )
            )
        ).scalar_one_or_none()


@pytest.mark.e2e
@pytest.mark.asyncio
class TestReplay:
    async def test_retry_returns_same_response_and_does_not_duplicate(self, api):
        account = await _create_account(api, balance=1000.0)
        key = str(uuid4())
        body = _expense(account["account_uuid"], 100.0)

        first = await api.client.post(
            "/transaction/", json=body, headers=with_idempotency_key(bearer(), key)
        )
        retry = await api.client.post(
            "/transaction/", json=body, headers=with_idempotency_key(bearer(), key)
        )

        assert first.status_code == 200, first.text
        assert retry.status_code == first.status_code
        # Mismo JSON (en MySQL el orden de las claves puede cambiar: la columna es JSON).
        assert retry.json() == first.json()
        assert "idempotent-replayed" not in first.headers
        assert retry.headers["idempotent-replayed"] == "true"
        assert await api.count(TransactionModel) == 1
        assert await _balance(api, account["account_uuid"]) == 900.0

    async def test_transfer_retry_moves_money_once(self, api):
        source = await _create_account(api, balance=1000.0)
        destination = await _create_account(api, balance=0.0)
        key = str(uuid4())
        body = {
            "source_account_uuid": source["account_uuid"],
            "destination_account_uuid": destination["account_uuid"],
            "amount": 250.0,
            "transfer_date": "2026-11-01",
        }

        responses = [
            await api.client.post(
                "/transfers/", json=body, headers=with_idempotency_key(bearer(), key)
            )
            for _ in range(3)
        ]

        assert [r.status_code for r in responses] == [201, 201, 201]
        assert responses[1].json() == responses[0].json() == responses[2].json()
        # Una transferencia son dos movimientos (salida y entrada), no seis.
        assert await api.count(TransactionModel) == 2
        assert await _balance(api, source["account_uuid"]) == 750.0
        assert await _balance(api, destination["account_uuid"]) == 250.0

    async def test_response_is_stored_with_status_and_body(self, api):
        key = str(uuid4())
        response = await api.client.post(
            "/account",
            json={
                "name": "Guardada",
                "account_type": "CASH",
                "bank_id": 1,
                "initial_balance": 10,
                "currency": "MXN",
            },
            headers=with_idempotency_key(bearer(), key),
        )

        row = await _key_row(api, 1, key)
        assert row is not None
        assert row.status_code == 201
        assert row.response == response.json()
        assert len(row.request_hash) == 64

    async def test_api_key_auth_is_protected_too(self, api):
        """Las tools del MCP llegan con X-API-Key: la clave aplica igual."""
        account = await _create_account(api)
        created = await api.client.post(
            "/api-keys/",
            json={"name": "mcp", "scopes": ["transactions:write"]},
            headers=with_idempotency_key(bearer()),
        )
        api_key_headers = {"X-API-Key": created.json()["raw_key"]}
        key = str(uuid4())
        body = _expense(account["account_uuid"], 40.0)

        first = await api.client.post(
            "/transaction/", json=body, headers=with_idempotency_key(api_key_headers, key)
        )
        retry = await api.client.post(
            "/transaction/", json=body, headers=with_idempotency_key(api_key_headers, key)
        )

        assert first.status_code == 200, first.text
        assert retry.json() == first.json()
        assert await api.count(TransactionModel) == 1

    async def test_api_key_creation_retry_does_not_store_the_secret(self, api):
        key = str(uuid4())
        body = {"name": "app", "scopes": ["transactions:read"]}

        first = await api.client.post(
            "/api-keys/", json=body, headers=with_idempotency_key(bearer(), key)
        )
        retry = await api.client.post(
            "/api-keys/", json=body, headers=with_idempotency_key(bearer(), key)
        )

        assert first.status_code == retry.status_code == 201
        assert first.json()["raw_key"].startswith("moon_")
        assert retry.json() == {**first.json(), "raw_key": None}
        assert await api.count(APIKeyModel) == 1
        row = await _key_row(api, 1, key)
        assert row is not None
        assert first.json()["raw_key"] not in str(row.response)


@pytest.mark.e2e
@pytest.mark.asyncio
class TestKeyValidation:
    async def test_missing_header_on_create_is_a_validation_error(self, api):
        account = await _create_account(api)

        response = await api.client.post(
            "/transaction/", json=_expense(account["account_uuid"]), headers=bearer()
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error_code"] == "VALIDATION_ERROR"
        assert data["details"][0]["loc"] == ["header", IDEMPOTENCY_KEY_HEADER]
        assert await api.count(TransactionModel) == 0

    @pytest.mark.parametrize("value", ["", "abc", "123", "not-a-uuid-at-all"])
    async def test_non_uuid_header_is_a_validation_error(self, api, value):
        account = await _create_account(api)

        response = await api.client.post(
            "/transaction/",
            json=_expense(account["account_uuid"]),
            headers={**bearer(), IDEMPOTENCY_KEY_HEADER: value},
        )

        assert response.status_code == 422
        assert response.json()["error_code"] == "VALIDATION_ERROR"
        assert await api.count(TransactionModel) == 0

    async def test_same_key_with_different_body_is_rejected(self, api):
        account = await _create_account(api)
        key = str(uuid4())
        await api.client.post(
            "/transaction/",
            json=_expense(account["account_uuid"], 100.0),
            headers=with_idempotency_key(bearer(), key),
        )

        response = await api.client.post(
            "/transaction/",
            json=_expense(account["account_uuid"], 999.0),
            headers=with_idempotency_key(bearer(), key),
        )

        assert response.status_code == 422
        assert response.json()["error_code"] == "IDEMPOTENCY_KEY_REUSED"
        assert await api.count(TransactionModel) == 1
        assert await _balance(api, account["account_uuid"]) == 900.0

    async def test_same_key_on_another_endpoint_is_rejected(self, api):
        key = str(uuid4())
        account = await api.client.post(
            "/account",
            json={
                "name": "Una",
                "account_type": "CASH",
                "bank_id": 1,
                "initial_balance": 0,
                "currency": "MXN",
            },
            headers=with_idempotency_key(bearer(), key),
        )
        assert account.status_code == 201

        response = await api.client.post(
            "/budgets/",
            json={
                "name": "Una",
                "limit_amount": 100,
                "period": "mensual",
                "category_id": 1,
            },
            headers=with_idempotency_key(bearer(), key),
        )

        assert response.status_code == 422
        assert response.json()["error_code"] == "IDEMPOTENCY_KEY_REUSED"

    async def test_keys_are_scoped_per_user(self, api):
        key = str(uuid4())
        accounts = {}
        for user_id in (1, 2):
            response = await api.client.post(
                "/account",
                json={
                    "name": "Misma clave",
                    "account_type": "CASH",
                    "bank_id": 1,
                    "initial_balance": 50,
                    "currency": "MXN",
                },
                headers=with_idempotency_key(bearer(user_id), key),
            )
            assert response.status_code == 201, response.text
            assert "idempotent-replayed" not in response.headers
            accounts[user_id] = response.json()

        assert accounts[1]["account_uuid"] != accounts[2]["account_uuid"]
        assert await api.count(IdempotencyKeyModel, IdempotencyKeyModel.key == key) == 2


@pytest.mark.e2e
@pytest.mark.asyncio
class TestFailures:
    async def test_handler_error_leaves_no_key_and_retry_executes(self, api):
        source = await _create_account(api, balance=10.0)
        destination = await _create_account(api, balance=0.0)
        key = str(uuid4())
        body = {
            "source_account_uuid": source["account_uuid"],
            "destination_account_uuid": destination["account_uuid"],
            "amount": 100.0,
            "transfer_date": "2026-11-01",
        }

        failed = await api.client.post(
            "/transfers/", json=body, headers=with_idempotency_key(bearer(), key)
        )
        assert failed.status_code == 422
        assert failed.json()["error_code"] == "INSUFFICIENT_FUNDS"
        assert await _key_row(api, 1, key) is None

        await api.client.post(
            "/transaction/",
            json={**_expense(source["account_uuid"], 500.0), "transaction_type": "INCOME", "category_id": 2},
            headers=with_idempotency_key(bearer()),
        )
        retried = await api.client.post(
            "/transfers/", json=body, headers=with_idempotency_key(bearer(), key)
        )

        assert retried.status_code == 201, retried.text
        assert "idempotent-replayed" not in retried.headers
        assert await _balance(api, destination["account_uuid"]) == 100.0

    async def test_error_before_the_handler_transaction_leaves_no_key(self, api):
        """SameAccountTransferError salta antes del `async with uow` del handler."""
        account = await _create_account(api)
        key = str(uuid4())

        response = await api.client.post(
            "/transfers/",
            json={
                "source_account_uuid": account["account_uuid"],
                "destination_account_uuid": account["account_uuid"],
                "amount": 1.0,
            },
            headers=with_idempotency_key(bearer(), key),
        )

        assert response.status_code == 409
        assert await _key_row(api, 1, key) is None

    async def test_key_without_stored_response_returns_409(self, api, monkeypatch):
        """El proceso "muere" entre el commit del handler y el guardado de la respuesta."""
        account = await _create_account(api, balance=1000.0)
        key = str(uuid4())
        body = _expense(account["account_uuid"], 100.0)

        async def crash(*args, **kwargs):
            raise RuntimeError("worker killed")

        with monkeypatch.context() as patch:
            patch.setattr(SQLAlchemyIdempotencyRepository, "save_response", crash)
            crashed = await api.client.post(
                "/transaction/", json=body, headers=with_idempotency_key(bearer(), key)
            )
        assert crashed.status_code == 500

        # El commit del handler guardó la clave y el movimiento juntos.
        row = await _key_row(api, 1, key)
        assert row is not None and row.status_code is None
        assert await api.count(TransactionModel) == 1

        retry = await api.client.post(
            "/transaction/", json=body, headers=with_idempotency_key(bearer(), key)
        )

        assert retry.status_code == 409
        assert retry.json()["error_code"] == "IDEMPOTENCY_KEY_IN_USE"
        assert await api.count(TransactionModel) == 1
        assert await _balance(api, account["account_uuid"]) == 900.0


@pytest.mark.e2e
@pytest.mark.asyncio
class TestOptionalOnUpdates:
    async def _transaction(self, api: IsolatedApp) -> dict:
        account = await _create_account(api, balance=1000.0)
        response = await api.client.post(
            "/transaction/",
            json=_expense(account["account_uuid"], 100.0),
            headers=with_idempotency_key(bearer()),
        )
        return response.json()

    async def test_put_and_delete_work_without_header(self, api):
        transaction = await self._transaction(api)

        updated = await api.client.put(
            f"/transaction/{transaction['uuid']}/",
            json={"description": "Editada"},
            headers=bearer(),
        )
        deleted = await api.client.delete(
            f"/transaction/{transaction['uuid']}/", headers=bearer()
        )

        assert updated.status_code == 200, updated.text
        assert updated.json()["description"] == "Editada"
        assert deleted.status_code == 204
        # Sin clave no se guarda nada.
        assert await api.count(IdempotencyKeyModel) == 2  # cuenta + transacción

    async def test_delete_with_header_is_replayed(self, api):
        transaction = await self._transaction(api)
        key = str(uuid4())

        first = await api.client.delete(
            f"/transaction/{transaction['uuid']}/",
            headers=with_idempotency_key(bearer(), key),
        )
        retry = await api.client.delete(
            f"/transaction/{transaction['uuid']}/",
            headers=with_idempotency_key(bearer(), key),
        )
        without_key = await api.client.delete(
            f"/transaction/{transaction['uuid']}/", headers=bearer()
        )

        assert first.status_code == 204
        # Sin la clave, el segundo DELETE respondería 404.
        assert retry.status_code == 204
        assert retry.headers["idempotent-replayed"] == "true"
        assert retry.content == b""
        assert without_key.status_code == 404

    async def test_patch_with_header_is_replayed(self, api):
        account = await _create_account(api)
        key = str(uuid4())
        url = f"/account/{account['account_uuid']}/status/"

        first = await api.client.patch(url, headers=with_idempotency_key(bearer(), key))
        retry = await api.client.patch(url, headers=with_idempotency_key(bearer(), key))

        # Es un toggle: sin la clave, el reintento volvería a activar la cuenta.
        assert first.status_code == 200
        assert first.json()["is_active"] is False
        assert retry.json() == first.json()

    async def test_invalid_optional_header_is_a_validation_error(self, api):
        transaction = await self._transaction(api)

        response = await api.client.delete(
            f"/transaction/{transaction['uuid']}/",
            headers={**bearer(), IDEMPOTENCY_KEY_HEADER: "nope"},
        )

        assert response.status_code == 422
        assert response.json()["error_code"] == "VALIDATION_ERROR"


@pytest.mark.e2e
@pytest.mark.asyncio
class TestPurge:
    async def test_purge_removes_only_keys_older_than_24_hours(self, api):
        from datetime import UTC, datetime, timedelta

        from application.idempotency.commands.purge_idempotency_keys import (
            PurgeIdempotencyKeysCommand,
            PurgeIdempotencyKeysHandler,
        )
        from infrastructure.database.repositories.sqlalchemy_unit_of_work import (
            SQLAlchemyUnitOfWork,
        )

        now = datetime.now(UTC)
        async with api.sessions() as session:
            repo = SQLAlchemyIdempotencyRepository(session)
            for key, age in (("old", timedelta(hours=25)), ("new", timedelta(hours=1))):
                await repo.try_claim(
                    user_id=1, key=key, request_hash="0" * 64, created_at=now - age
                )
            await session.commit()

        async with api.sessions() as session:
            deleted = await PurgeIdempotencyKeysHandler(
                SQLAlchemyIdempotencyRepository(session), SQLAlchemyUnitOfWork(session)
            ).handle(PurgeIdempotencyKeysCommand(now=now))

        assert deleted == 1
        assert await _key_row(api, 1, "old") is None
        assert await _key_row(api, 1, "new") is not None


def test_scheduler_registers_daily_purge(monkeypatch):
    from infrastructure.scheduler.jobs import purge_idempotency_keys_job
    from infrastructure.scheduler.service import SchedulerService

    service = SchedulerService()
    monkeypatch.setattr(service.scheduler, "start", lambda: None)
    service.start()

    job = service.scheduler.get_job("purge_idempotency_keys_job")
    assert job is not None
    assert job.func is purge_idempotency_keys_job
    assert str(job.trigger) == "cron[hour='3', minute='30']"
