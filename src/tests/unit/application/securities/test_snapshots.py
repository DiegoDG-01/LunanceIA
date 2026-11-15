"""Reconstrucción de fotos diarias con repositorios reales: qué se rehace y desde cuándo."""

from datetime import date, timedelta
from decimal import Decimal

from application.interfaces.market_data import ProviderName
from application.securities.commands.rebuild_snapshots import (
    RebuildSnapshotsCommand,
    RebuildSnapshotsHandler,
)
from application.securities.services.price_sync import InstrumentPriceSync
from domain.entities.securities.exchange_rate import ExchangeRate
from domain.entities.securities.instrument_price import InstrumentPrice
from domain.objects.enums import Market, TradeType
from infrastructure.database.repositories.sqlalchemy_instrument_repository import (
    SQLAlchemyInstrumentProviderSymbolRepository,
)
from infrastructure.database.repositories.sqlalchemy_trade_repository import (
    SQLAlchemyHoldingSnapshotRepository,
)

from .fakes import FakeGateway, closes, routed
from .test_trades import (  # noqa: F401 - fixtures
    D,
    USER_ID,
    account,
    env,
    make_account,
    make_instrument,
    walmex,
)


def nov(day: int) -> date:
    return date(2026, 11, day)


def handler(env) -> RebuildSnapshotsHandler:
    return RebuildSnapshotsHandler(
        holding_repository=env.holdings,
        trade_repository=env.trades,
        snapshot_repository=SQLAlchemyHoldingSnapshotRepository(env.db),
        instrument_repository=env.instruments,
        price_repository=env.prices,
        fx_repository=env.fx,
        uow=env.uow(),
    )


async def rebuild(env, day: int, **kw):
    return await handler(env).handle(RebuildSnapshotsCommand(as_of=nov(day), **kw))


async def snapshots(env, account, instrument, start=1, end=30):
    holding = await env.holdings.get(account.id, instrument.id)
    rows = await SQLAlchemyHoldingSnapshotRepository(env.db).get_range(
        holding.id, nov(start), nov(end)
    )
    return holding, {s.snapshot_date.day: s for s in rows}


async def price(env, instrument, day, close):
    await env.prices.save_many(
        [
            InstrumentPrice(
                instrument_id=instrument.id,
                price_date=nov(day),
                close=D(close),
                provider="databursatil",
            )
        ]
    )


class TestBuild:
    async def test_first_build_from_the_first_trade_until_today(self, env, account, walmex):
        await env.record(account, walmex, day=3, quantity=D("10"), price=D("50"))
        await price(env, walmex, 3, "51")
        await price(env, walmex, 6, "53")

        stats = await rebuild(env, 9)

        holding, days = await snapshots(env, account, walmex)
        assert sorted(days) == list(range(3, 10))
        assert days[3].market_value == D("510.00")
        assert days[8].close == D("53.000000") and days[8].price_date == nov(6)
        assert (holding.snapshots_through, holding.snapshots_dirty_from) == (nov(9), None)
        assert (stats.rebuilt, stats.snapshots) == (1, 7)

    async def test_next_run_only_adds_the_new_days(self, env, account, walmex):
        await env.record(account, walmex, day=3, quantity=D("10"), price=D("50"))
        await rebuild(env, 9)
        stats = await rebuild(env, 11)
        assert stats.snapshots == 2
        assert (await rebuild(env, 11)).holdings == 0

    async def test_editing_an_old_trade_rebuilds_from_its_date(self, env, account, walmex):
        bought = await env.record(account, walmex, day=3, quantity=D("10"), price=D("50"))
        await env.record(account, walmex, day=7, quantity=D("5"), price=D("52"))
        await rebuild(env, 10)

        await env.update(bought.trade.uuid, day=5, quantity=D("10"), price=D("50"))
        holding = await env.holdings.get(account.id, walmex.id)
        assert holding.snapshots_dirty_from == nov(3)

        stats = await rebuild(env, 10)
        holding, days = await snapshots(env, account, walmex)
        assert stats.snapshots == 6  # del 5 al 10: los días 3 y 4 ya no tienen títulos
        assert 3 not in days and 4 not in days
        assert days[5].quantity == D("10") and days[7].quantity == D("15")

    async def test_closed_holding_stops_at_the_last_trade(self, env, account, walmex):
        await env.record(account, walmex, day=3, quantity=D("10"), price=D("50"))
        await env.record(account, walmex, TradeType.SELL, day=6, quantity=D("10"), price=D("55"))
        await rebuild(env, 12)
        holding, days = await snapshots(env, account, walmex)
        assert max(days) == 6
        assert days[6].quantity == 0 and days[6].realized_pnl == D("50.00")
        assert holding.snapshots_through == nov(6)
        assert (await rebuild(env, 13)).holdings == 0

        # Un dividendo después de vender extiende las fotos hasta ese día.
        await env.record(account, walmex, TradeType.DIVIDEND, day=8, gross_amount=D("4"))
        await rebuild(env, 13)
        _, days = await snapshots(env, account, walmex)
        assert max(days) == 8 and days[8].dividends == D("4.00")

    async def test_deleting_the_final_sale_reopens_until_today(self, env, account, walmex):
        await env.record(account, walmex, day=3, quantity=D("10"), price=D("50"))
        sold = await env.record(
            account, walmex, TradeType.SELL, day=6, quantity=D("10"), price=D("55")
        )
        await rebuild(env, 12)
        await env.delete(sold.trade.uuid)
        await rebuild(env, 12)
        _, days = await snapshots(env, account, walmex)
        assert max(days) == 12 and days[12].quantity == D("10")

    async def test_only_one_instrument(self, env, account, walmex):
        funo = await make_instrument(env, "FUNO11")
        await env.record(account, walmex, day=3, quantity=D("1"), price=D("50"))
        await env.record(account, funo, day=3, quantity=D("1"), price=D("30"))
        stats = await rebuild(env, 5, instrument_id=walmex.id)
        assert stats.rebuilt == 1
        assert (await rebuild(env, 5)).rebuilt == 1


class TestMarks:
    async def test_a_corrected_close_marks_holdings_that_already_have_that_day(
        self, env, account, walmex
    ):
        await env.record(account, walmex, day=3, quantity=D("10"), price=D("50"))
        await price(env, walmex, 4, "51")
        await rebuild(env, 9)

        gateway = FakeGateway()
        gateway.closes["WALMEX*"] = routed(
            ProviderName.DATABURSATIL, "WALMEX*", closes((nov(4), "51.50"), (nov(10), "52"))
        )
        sync = InstrumentPriceSync(
            instrument_repository=env.instruments,
            symbol_repository=SQLAlchemyInstrumentProviderSymbolRepository(env.db),
            price_repository=env.prices,
            gateway=gateway,
            holding_repository=env.holdings,
        )
        await sync.sync(await env.instruments.get_by_id(walmex.id), nov(4), nov(10))
        env.db.expire_all()
        holding = await env.holdings.get(account.id, walmex.id)
        assert holding.snapshots_dirty_from == nov(4)

        await rebuild(env, 10)
        _, days = await snapshots(env, account, walmex)
        assert days[5].market_value == D("515.00")
        assert days[10].market_value == D("520.00")

    async def test_new_closes_after_the_last_snapshot_do_not_mark(
        self, env, account, walmex
    ):
        await env.record(account, walmex, day=3, quantity=D("10"), price=D("50"))
        await rebuild(env, 9)
        await env.holdings.mark_dirty_for_instrument(walmex.id, nov(10))
        env.db.expire_all()
        assert (await env.holdings.get(account.id, walmex.id)).snapshots_dirty_from is None

    async def test_fx_changes_mark_dollar_holdings(self, env, walmex):
        dollars = await make_account(env, balance="1000", currency="USD")
        pesos = await make_account(env)
        aapl = await make_instrument(env, "AAPL", Market.US, "USD")
        await env.record(dollars, aapl, day=3, quantity=D("1"), price=D("200"))
        await env.record(pesos, walmex, day=3, quantity=D("1"), price=D("50"))
        await price(env, aapl, 3, "210")
        await env.fx.save_many(
            [ExchangeRate(base="USD", quote="MXN", rate_date=nov(3), rate=D("18.5"), provider="banxico")]
        )
        await rebuild(env, 6)
        _, days = await snapshots(env, dollars, aapl)
        assert days[6].market_value_mxn == D("3885.00")

        await env.holdings.mark_dirty_for_currency("USD", nov(5))
        env.db.expire_all()
        assert (await env.holdings.get(dollars.id, aapl.id)).snapshots_dirty_from == nov(5)
        assert (await env.holdings.get(pesos.id, walmex.id)).snapshots_dirty_from is None

    async def test_a_newer_mark_survives_finishing_an_older_one(self, env, account, walmex):
        await env.record(account, walmex, day=3, quantity=D("1"), price=D("50"))
        await rebuild(env, 9)
        holding = await env.holdings.get(account.id, walmex.id)
        await env.holdings.mark_dirty_for_instrument(walmex.id, nov(5))
        # Otra marca más vieja llega antes de terminar la de 5: no se borra.
        await env.holdings.mark_dirty_for_instrument(walmex.id, nov(4))
        await env.holdings.finish_snapshots(holding.id, through=nov(9), dirty_from=nov(5))
        env.db.expire_all()
        assert (await env.holdings.get(account.id, walmex.id)).snapshots_dirty_from == nov(4)
