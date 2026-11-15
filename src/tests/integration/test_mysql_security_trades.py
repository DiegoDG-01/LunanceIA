"""Operaciones simultáneas sobre el mismo valor y cuenta contra MySQL 8 real (InnoDB).

Con REPEATABLE READ, la primera lectura sin bloqueo fija la foto de la transacción. Si un
handler leyera antes de esperar el bloqueo de la cuenta, la segunda operación no vería la
primera y recalcularía la tenencia sin ella. Arranca un `mysql:8.0` desechable con Docker;
si Docker no está disponible, se salta.

    uv run pytest -q -m integration src/tests/integration/test_mysql_security_trades.py
"""

import asyncio
from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

from application.securities.services.trade_bookkeeper import TradeBookkeeper
from domain.objects.enums import InstrumentType, Market
from infrastructure.database.models.account import AccountModel
from infrastructure.database.models.instrument import InstrumentModel
from infrastructure.database.models.security_trade import SecurityHoldingModel
from main import app
from presentation.dependencies.security_deps import get_instrument_tracker

from ..idempotency import with_idempotency_key
from ..isolated_app import bearer, isolated_app
from .test_mysql_idempotency import mysql_url  # noqa: F401 - fixture de módulo

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def api(mysql_url):  # noqa: F811
    engine = create_async_engine(mysql_url, pool_size=5, max_overflow=0)
    try:
        async with isolated_app(engine) as harness:

            async def no_backfill(instrument_id: int, since: date) -> None:
                return None

            app.dependency_overrides[get_instrument_tracker] = lambda: no_backfill
            yield harness
    finally:
        await engine.dispose()


@pytest.fixture
def slow_recompute(monkeypatch):
    """La primera operación se queda a mitad (con la cuenta bloqueada) mientras llega la
    segunda."""
    original = TradeBookkeeper.recompute

    async def slow(self, context, **kwargs):
        await asyncio.sleep(0.4)
        return await original(self, context, **kwargs)

    monkeypatch.setattr(TradeBookkeeper, "recompute", slow)


async def _setup(api) -> tuple[str, str]:
    response = await api.client.post(
        "/account",
        json={
            "name": "Casa de bolsa",
            "account_type": "INVESTMENT",
            "bank_id": 1,
            "initial_balance": 20000,
            "currency": "MXN",
        },
        headers=with_idempotency_key(bearer()),
    )
    assert response.status_code == 201, response.text
    async with api.sessions() as session:
        instrument = InstrumentModel(
            market=Market.BMV,
            symbol="WALMEX*",
            name="WAL - MART DE MEXICO",
            instrument_type=InstrumentType.STOCK,
            currency="MXN",
            is_active=True,
        )
        session.add(instrument)
        await session.commit()
        return response.json()["account_uuid"], instrument.uuid


def _trade(account_uuid, instrument_uuid, kind, day, quantity, price="50"):
    return {
        "account_uuid": account_uuid,
        "instrument_uuid": instrument_uuid,
        "trade_type": kind,
        "trade_date": f"2026-11-{day:02d}",
        "quantity": quantity,
        "price": price,
    }


async def test_concurrent_buys_both_count(api, slow_recompute):
    account_uuid, instrument_uuid = await _setup(api)

    first, second = await asyncio.gather(
        api.client.post(
            "/securities/trades/",
            json=_trade(account_uuid, instrument_uuid, "BUY", 3, "100"),
            headers=with_idempotency_key(bearer()),
        ),
        api.client.post(
            "/securities/trades/",
            json=_trade(account_uuid, instrument_uuid, "BUY", 4, "50"),
            headers=with_idempotency_key(bearer()),
        ),
    )
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text

    async with api.sessions() as session:
        holding = (await session.execute(select(SecurityHoldingModel))).scalar_one()
        account = (
            await session.execute(
                select(AccountModel).where(AccountModel.uuid == account_uuid)
            )
        ).scalar_one()
    assert holding.quantity == Decimal("150")
    assert holding.cost_basis == Decimal("7500.00")
    assert account.current_balance == Decimal("12500.00")


async def test_concurrent_sales_cannot_oversell(api, slow_recompute):
    account_uuid, instrument_uuid = await _setup(api)
    bought = await api.client.post(
        "/securities/trades/",
        json=_trade(account_uuid, instrument_uuid, "BUY", 3, "100"),
        headers=with_idempotency_key(bearer()),
    )
    assert bought.status_code == 201, bought.text

    responses = await asyncio.gather(
        *(
            api.client.post(
                "/securities/trades/",
                json=_trade(account_uuid, instrument_uuid, "SELL", 5, "60", "55"),
                headers=with_idempotency_key(bearer()),
            )
            for _ in range(2)
        )
    )
    assert sorted(r.status_code for r in responses) == [201, 409]
    refused = next(r for r in responses if r.status_code == 409)
    assert refused.json()["error_code"] == "INSUFFICIENT_SHARES"

    async with api.sessions() as session:
        holding = (await session.execute(select(SecurityHoldingModel))).scalar_one()
    assert holding.quantity == Decimal("40")
