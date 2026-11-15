"""Patrimonio e historia de lo invertido contra MySQL 8 real.

Las consultas del portafolio usan UNION ALL, un join contra una subconsulta agrupada y
SUM(CASE ...): aquí se comprueba que MySQL las acepta y suma igual que SQLite. Arranca un
`mysql:8.0` desechable con Docker; si Docker no está disponible, se salta.

    uv run pytest -q -m integration src/tests/integration/test_mysql_portfolio.py
"""

from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

from application.securities.commands.rebuild_snapshots import (
    RebuildSnapshotsCommand,
    RebuildSnapshotsHandler,
)
from domain.objects.enums import (
    InstrumentType,
    InterestType,
    Market,
    PositionStatus,
    PositionType,
)
from infrastructure.database.models import (
    AccountModel,
    ExchangeRateModel,
    InstrumentModel,
    InstrumentPriceModel,
    InvestmentPositionModel,
    InvestmentYieldModel,
)
from infrastructure.database.repositories.sqlalchemy_instrument_repository import (
    SQLAlchemyInstrumentRepository,
)
from infrastructure.database.repositories.sqlalchemy_price_repository import (
    SQLAlchemyExchangeRateRepository,
    SQLAlchemyInstrumentPriceRepository,
)
from infrastructure.database.repositories.sqlalchemy_trade_repository import (
    SQLAlchemyHoldingSnapshotRepository,
    SQLAlchemySecurityHoldingRepository,
    SQLAlchemySecurityTradeRepository,
)
from infrastructure.database.repositories.sqlalchemy_unit_of_work import (
    SQLAlchemyUnitOfWork,
)
from main import app
from presentation.dependencies.security_deps import get_instrument_tracker

from ..idempotency import with_idempotency_key
from ..isolated_app import bearer, isolated_app
from .test_mysql_idempotency import mysql_url  # noqa: F401 - fixture de módulo

pytestmark = pytest.mark.integration

D = Decimal


def nov(day: int) -> date:
    return date(2026, 11, day)


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


async def _account(api, currency: str, balance: int) -> int:
    response = await api.client.post(
        "/account",
        json={
            "name": f"Inversiones {currency}",
            "account_type": "INVESTMENT",
            "bank_id": 1,
            "initial_balance": balance,
            "currency": currency,
        },
        headers=with_idempotency_key(bearer()),
    )
    assert response.status_code == 201, response.text
    async with api.sessions() as session:
        return (
            await session.execute(
                select(AccountModel.id).where(
                    AccountModel.uuid == response.json()["account_uuid"]
                )
            )
        ).scalar_one()


def _position(account_id: int, currency: str, balance: str) -> InvestmentPositionModel:
    return InvestmentPositionModel(
        account_id=account_id,
        name=f"Apartado {currency}",
        position_type=PositionType.ON_DEMAND,
        status=PositionStatus.ACTIVE,
        balance=D(balance),
        accrued_yield=D(0),
        currency=currency,
        annual_rate=D(10),
        interest_type=InterestType.COMPOUND,
        start_date=date(2026, 10, 1),
    )


async def _setup(api) -> None:
    pesos = await _account(api, "MXN", 20000)
    dollars = await _account(api, "USD", 100)
    async with api.sessions() as session:
        walmex = InstrumentModel(
            market=Market.BMV,
            symbol="WALMEX*",
            name="WAL - MART DE MEXICO",
            instrument_type=InstrumentType.STOCK,
            currency="MXN",
            is_active=True,
        )
        session.add(walmex)
        await session.commit()
        walmex_uuid, walmex_id = walmex.uuid, walmex.id

    response = await api.client.post(
        "/securities/trades/",
        json={
            "account_uuid": (await _uuid(api, pesos)),
            "instrument_uuid": walmex_uuid,
            "trade_type": "BUY",
            "trade_date": "2026-11-03",
            "quantity": "10",
            "price": "50",
        },
        headers=with_idempotency_key(bearer()),
    )
    assert response.status_code == 201, response.text

    async with api.sessions() as session:
        for day, close in ((3, "51"), (10, "55")):
            session.add(
                InstrumentPriceModel(
                    instrument_id=walmex_id,
                    price_date=nov(day),
                    close=D(close),
                    is_trading_day=True,
                    provider="databursatil",
                )
            )
        for day, rate in ((2, "18"), (9, "19")):
            session.add(
                ExchangeRateModel(
                    base="USD",
                    quote="MXN",
                    rate_date=nov(day),
                    rate=D(rate),
                    provider="banxico",
                )
            )
        for account_id, currency, balance, yields in (
            (pesos, "MXN", "1002", {date(2026, 10, 30): "1000", nov(5): "1002"}),
            (dollars, "USD", "50", {nov(4): "50"}),
        ):
            position = _position(account_id, currency, balance)
            session.add(position)
            await session.flush()
            for day, value in yields.items():
                session.add(
                    InvestmentYieldModel(
                        account_id=account_id,
                        position_id=position.id,
                        yield_date=day,
                        principal_amount=D(value),
                        yield_amount=D("0.10"),
                        cumulative_balance=D(value),
                        annual_rate=D(10),
                        interest_type=InterestType.COMPOUND,
                    )
                )
        await session.commit()

    async with api.sessions() as session:
        await RebuildSnapshotsHandler(
            holding_repository=SQLAlchemySecurityHoldingRepository(session),
            trade_repository=SQLAlchemySecurityTradeRepository(session),
            snapshot_repository=SQLAlchemyHoldingSnapshotRepository(session),
            instrument_repository=SQLAlchemyInstrumentRepository(session),
            price_repository=SQLAlchemyInstrumentPriceRepository(session),
            fx_repository=SQLAlchemyExchangeRateRepository(session),
            uow=SQLAlchemyUnitOfWork(session),
        ).handle(RebuildSnapshotsCommand(as_of=nov(12)))


async def _uuid(api, account_id: int) -> str:
    async with api.sessions() as session:
        return (
            await session.execute(
                select(AccountModel.uuid).where(AccountModel.id == account_id)
            )
        ).scalar_one()


async def test_history_summary_and_dashboard(api):
    await _setup(api)

    response = await api.client.get(
        "/securities/portfolio/history",
        params={"from": "2026-11-01", "to": "2026-11-12"},
        headers=bearer(),
    )
    assert response.status_code == 200, response.text
    totals = {d["date"]: (d["total"], d["complete"]) for d in response.json()["days"]}
    assert totals["2026-11-01"] == ("1000.00", True)  # el apartado, del 30 de octubre
    assert totals["2026-11-03"] == ("1510.00", True)  # + 10 WALMEX a 51
    assert totals["2026-11-04"] == ("2410.00", True)  # + 50 USD × 18
    assert totals["2026-11-09"] == ("2462.00", True)  # 1002 + 50 × 19 + 510
    assert totals["2026-11-12"] == ("2502.00", True)  # WALMEX a 55 desde el 10

    summary = await api.client.get("/securities/portfolio/", headers=bearer())
    assert summary.status_code == 200, summary.text
    body = summary.json()
    # 20,000 − 500 de la compra + 100 USD × 19.
    assert body["cash"] == "21400.00"
    assert body["positions"] == "1952.00"
    assert body["securities"] == "550.00"
    assert body["net_worth"] == "23902.00"
    assert body["fx_rates"] == {"USD": "19.00000000"}

    dashboard = await api.client.get("/dashboard/", headers=bearer())
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["net_worth"]["net_worth"] == "23902.00"
