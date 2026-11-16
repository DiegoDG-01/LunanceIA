"""Sincronización de precios, tipo de cambio y catálogo con repositorios reales (SQLite) y un
gateway en memoria."""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast

import pytest

from application.interfaces.market_data import (
    FxRate,
    InstrumentListing,
    NoProviderAvailable,
    ProviderAttempt,
    ProviderName,
)
from application.securities.commands.sync_instrument_catalog import (
    SyncInstrumentCatalogCommand,
    SyncInstrumentCatalogHandler,
)
from application.securities.commands.sync_market_data import (
    SyncMarketDataCommand,
    SyncMarketDataHandler,
    price_window_start,
)
from application.securities.commands.track_instrument import (
    TrackInstrumentCommand,
    TrackInstrumentHandler,
)
from application.securities.currency_demand import CurrencyDemandRepository
from application.securities.queries.search_instruments import (
    SearchInstrumentsHandler,
    SearchInstrumentsQuery,
)
from application.securities.services.business_days import subtract_business_days
from application.securities.services.price_sync import InstrumentPriceSync
from domain.entities.securities.instrument import Instrument
from domain.objects.enums import InstrumentType, Market, ProviderSymbolStatus
from domain.repositories.unit_of_work import AbstractUnitOfWork
from infrastructure.database.repositories.sqlalchemy_instrument_repository import (
    SQLAlchemyInstrumentProviderSymbolRepository,
    SQLAlchemyInstrumentRepository,
)
from infrastructure.database.repositories.sqlalchemy_price_repository import (
    SQLAlchemyExchangeRateRepository,
    SQLAlchemyInstrumentPriceRepository,
)

from .fakes import FakeGateway, closes, routed

D = ProviderName.DATABURSATIL
E = ProviderName.EODHD
NOW = datetime(2026, 11, 14, 1, 0, tzinfo=UTC)
MON, TUE, WED, THU, FRI = (date(2026, 11, d) for d in range(9, 14))


class CountingUnitOfWork(AbstractUnitOfWork):
    """`db_session` vive dentro de una transacción que se deshace al final de la prueba (y
    SQLite no maneja bien los savepoints): aquí solo se hace flush y se cuenta."""

    def __init__(self, db):
        self.db = db
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        await self.db.flush()
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class Env:
    def __init__(self, db, gateway: FakeGateway):
        self.db = db
        self.gateway = gateway
        self.instruments = SQLAlchemyInstrumentRepository(db)
        self.symbols = SQLAlchemyInstrumentProviderSymbolRepository(db)
        self.prices = SQLAlchemyInstrumentPriceRepository(db)
        self.fx = SQLAlchemyExchangeRateRepository(db)
        self.uow = CountingUnitOfWork(db)
        self.price_sync = InstrumentPriceSync(
            instrument_repository=self.instruments,
            symbol_repository=self.symbols,
            price_repository=self.prices,
            gateway=gateway,
            clock=lambda: NOW,
        )

    def sync_handler(self, demand=None) -> SyncMarketDataHandler:
        return SyncMarketDataHandler(
            instrument_repository=self.instruments,
            price_repository=self.prices,
            fx_repository=self.fx,
            price_sync=self.price_sync,
            gateway=self.gateway,
            uow=self.uow,
            currency_demand=demand,
            clock=lambda: NOW,
        )

    async def instrument(
        self,
        symbol="WALMEX*",
        *,
        market=Market.BMV,
        currency="MXN",
        tracked_since: date | None = MON,
        preferred: str | None = None,
        name="WAL - MART DE MEXICO",
    ) -> Instrument:
        return await self.instruments.save(
            Instrument(
                id=None,
                uuid=None,
                market=market,
                symbol=symbol,
                name=name,
                instrument_type=InstrumentType.STOCK,
                currency=currency,
                preferred_provider=preferred,
                tracked_since=tracked_since,
            )
        )

    async def saved(self, instrument: Instrument, start=MON, end=FRI):
        return {
            p.price_date: (p.close, p.provider)
            for p in await self.prices.get_range(cast(int, instrument.id), start, end)
        }


@pytest.fixture
def gateway():
    return FakeGateway()


@pytest.fixture
def env(db_session, gateway):
    return Env(db_session, gateway)


class TestBusinessDays:
    def test_skips_weekends(self):
        assert subtract_business_days(MON, 1) == date(2026, 11, 6)  # viernes
        assert subtract_business_days(FRI, 4) == MON
        assert subtract_business_days(date(2026, 11, 15), 1) == FRI  # domingo
        assert subtract_business_days(FRI, 0) == FRI

    def test_window_start(self):
        since = date(2026, 1, 5)
        # Sin precios: unos días antes del seguimiento.
        assert price_window_start(since, None, None, 10) == date(2025, 12, 29)
        # Con precios: la ventana de revisión desde el último día.
        assert price_window_start(since, since, FRI, 10) == date(2026, 10, 30)
        # Falta la historia del principio: todo otra vez.
        assert price_window_start(since, MON, FRI, 10) == date(2025, 12, 29)


class TestPriceSync:
    async def test_first_sync_fixes_the_provider_and_saves_prices(self, env, gateway):
        walmex = await env.instrument()
        gateway.closes["WALMEX*"] = routed(
            D, "WALMEX*", closes((MON, "54.10"), (TUE, "54.24"))
        )

        result = await env.price_sync.sync(walmex, MON, FRI)

        assert (result.provider, result.saved) == ("databursatil", 2)
        assert (await env.instruments.get_by_id(walmex.id)).preferred_provider == "databursatil"
        assert await env.saved(walmex) == {
            MON: (Decimal("54.100000"), "databursatil"),
            TUE: (Decimal("54.240000"), "databursatil"),
        }
        [symbol] = await env.symbols.get_for_instrument(walmex.id)
        assert (symbol.provider, symbol.provider_symbol, symbol.status) == (
            "databursatil",
            "WALMEX*",
            ProviderSymbolStatus.ACTIVE,
        )

    async def test_unsupported_provider_is_remembered_and_skipped(self, env, gateway):
        walmex = await env.instrument()
        gateway.closes["WALMEX*"] = routed(
            E,
            "WALMEX.MX",
            closes((MON, "54.1")),
            unsupported=(D,),
            attempts=(ProviderAttempt(D, "unsupported", "desconocida", "WALMEX*"),),
        )
        await env.price_sync.sync(walmex, MON, FRI)

        symbols = {s.provider: s for s in await env.symbols.get_for_instrument(walmex.id)}
        assert symbols["databursatil"].status is ProviderSymbolStatus.UNSUPPORTED
        assert symbols["eodhd"].provider_symbol == "WALMEX.MX"

        await env.price_sync.sync(await env.instruments.get_by_id(walmex.id), MON, FRI)
        last = gateway.calls[-1]
        assert last.skip == frozenset({D})
        assert last.provider_symbols == {E: "WALMEX.MX"}
        assert last.preferred is E

    async def test_fallback_fills_gaps_but_does_not_overwrite_the_preferred(
        self, env, gateway
    ):
        walmex = await env.instrument(preferred="databursatil")
        gateway.closes["WALMEX*"] = routed(D, "WALMEX*", closes((MON, "54.10")))
        await env.price_sync.sync(walmex, MON, FRI)

        # DataBursatil cae: EODHD responde con otro cierre para el lunes y uno nuevo.
        gateway.closes["WALMEX*"] = routed(
            E, "WALMEX.MX", closes((MON, "53.90"), (TUE, "54.30"))
        )
        result = await env.price_sync.sync(walmex, MON, FRI)

        assert result.saved == 1
        assert await env.saved(walmex) == {
            MON: (Decimal("54.100000"), "databursatil"),
            TUE: (Decimal("54.300000"), "eodhd"),
        }

        # DataBursatil vuelve y corrige el martes.
        gateway.closes["WALMEX*"] = routed(
            D, "WALMEX*", closes((MON, "54.10"), (TUE, "54.24"))
        )
        result = await env.price_sync.sync(walmex, MON, FRI)
        assert result.saved == 1  # el lunes no cambió
        assert await env.saved(walmex) == {
            MON: (Decimal("54.100000"), "databursatil"),
            TUE: (Decimal("54.240000"), "databursatil"),
        }

    async def test_preferred_that_drops_the_symbol_is_replaced(self, env, gateway):
        walmex = await env.instrument(preferred="databursatil")
        gateway.closes["WALMEX*"] = routed(
            E,
            "WALMEX.MX",
            closes((MON, "54.1")),
            unsupported=(D,),
            attempts=(ProviderAttempt(D, "unsupported", "", "WALMEX*"),),
        )
        await env.price_sync.sync(walmex, MON, FRI)
        assert (await env.instruments.get_by_id(walmex.id)).preferred_provider == "eodhd"

    async def test_holidays_keep_the_flag(self, env, gateway):
        walmex = await env.instrument()
        gateway.closes["WALMEX*"] = routed(
            D, "WALMEX*", closes((MON, "54.1"), trading=False)
        )
        await env.price_sync.sync(walmex, MON, FRI)
        [price] = await env.prices.get_range(walmex.id, MON, MON)
        assert price.is_trading_day is False


class TestSyncMarketData:
    async def test_syncs_tracked_instruments_only(self, env, gateway):
        await env.instrument("FUNO11", tracked_since=None)
        walmex = await env.instrument()
        gateway.closes["WALMEX*"] = routed(D, "WALMEX*", closes((MON, "54.1")))

        stats = await env.sync_handler().handle(SyncMarketDataCommand(as_of=FRI))

        assert (stats.instruments, stats.synced, stats.failed) == (1, 1, 0)
        assert [c.symbol for c in gateway.calls] == ["WALMEX*"]
        # Primera vez: desde unos días hábiles antes del seguimiento.
        assert gateway.calls[0].start == subtract_business_days(MON, 5)
        assert gateway.calls[0].end == FRI
        assert MON in await env.saved(walmex)

    async def test_later_runs_use_the_revision_window(self, env, gateway):
        walmex = await env.instrument(tracked_since=date(2026, 1, 5))
        gateway.closes["WALMEX*"] = routed(
            D, "WALMEX*", closes((date(2026, 1, 5), "60"), (THU, "54.1"))
        )
        await env.sync_handler().handle(SyncMarketDataCommand(as_of=FRI))
        await env.sync_handler().handle(
            SyncMarketDataCommand(as_of=FRI, revision_days=3)
        )
        assert gateway.calls[-1].start == MON  # jueves menos 3 días hábiles
        assert await env.prices.last_price_date(walmex.id) == THU

    async def test_one_failure_does_not_stop_the_others(self, env, gateway):
        await env.instrument("FUNO11")
        walmex = await env.instrument()
        gateway.closes["FUNO11"] = NoProviderAvailable("BMV:FUNO11", [])
        gateway.closes["WALMEX*"] = routed(D, "WALMEX*", closes((MON, "54.1")))

        stats = await env.sync_handler().handle(SyncMarketDataCommand(as_of=FRI))

        assert (stats.synced, stats.failed) == (1, 1)
        assert "BMV:FUNO11" in stats.failures[0]
        assert (env.uow.commits, env.uow.rollbacks) == (1, 1)
        assert MON in await env.saved(walmex)

    async def test_unexpected_error_is_contained(self, env, gateway):
        await env.instrument()
        gateway.closes["WALMEX*"] = RuntimeError("boom")
        stats = await env.sync_handler().handle(SyncMarketDataCommand(as_of=FRI))
        assert stats.failed == 1

    async def test_fx_only_when_a_dollar_instrument_is_tracked(self, env, gateway):
        gateway.rates = [FxRate(rate_date=THU, rate=Decimal("18.6188"))]
        await env.instrument()
        gateway.closes["WALMEX*"] = routed(D, "WALMEX*", [])
        await env.sync_handler().handle(SyncMarketDataCommand(as_of=FRI))
        assert gateway.fx_calls == []

        await env.instrument("AAPL", market=Market.US, currency="USD")
        gateway.closes["AAPL"] = routed(ProviderName.TWELVEDATA, "AAPL", [])
        stats = await env.sync_handler().handle(SyncMarketDataCommand(as_of=FRI))

        assert gateway.fx_calls == [(subtract_business_days(MON, 5), FRI)]
        assert stats.fx_saved == 1
        [rate] = await env.fx.get_range("USD", "MXN", MON, FRI)
        assert (rate.rate, rate.provider) == (Decimal("18.61880000"), "banxico")

        # Ya hay tipo de cambio desde antes del seguimiento: solo la ventana de revisión.
        await env.fx.save_many(
            [
                type(rate)(
                    base="USD",
                    quote="MXN",
                    rate_date=date(2026, 11, 2),
                    rate=Decimal("18.7"),
                    provider="banxico",
                )
            ]
        )
        await env.sync_handler().handle(
            SyncMarketDataCommand(as_of=FRI, revision_days=2)
        )
        assert gateway.fx_calls[-1] == (TUE, FRI)

    async def test_fx_for_accounts_and_positions_without_stocks(self, env, gateway):
        gateway.rates = [FxRate(rate_date=THU, rate=Decimal("20.5085"))]

        class Demand(CurrencyDemandRepository):
            async def since(self):
                # Cuentas en USD (solo días recientes) y un apartado en EUR desde el miércoles.
                return {"USD": None, "EUR": WED}

        stats = await env.sync_handler(Demand()).handle(SyncMarketDataCommand(as_of=FRI))

        assert gateway.fx_pairs == ["USD/MXN", "EUR/MXN"]
        assert gateway.fx_calls == [
            (subtract_business_days(FRI, 5), FRI),
            (subtract_business_days(WED, 5), FRI),
        ]
        assert stats.fx_saved == 2
        [euro] = await env.fx.get_range("EUR", "MXN", MON, FRI)
        assert euro.rate == Decimal("20.50850000")

    async def test_fx_failure_is_counted(self, env, gateway):
        await env.instrument("AAPL", market=Market.US, currency="USD")
        gateway.closes["AAPL"] = routed(ProviderName.TWELVEDATA, "AAPL", [])
        gateway.fx_error = NoProviderAvailable("USD/MXN", [])
        stats = await env.sync_handler().handle(SyncMarketDataCommand(as_of=FRI))
        assert stats.fx_failed == 1


class TestTrackInstrumentAfterTrade:
    """La operación ya fijó `tracked_since`; el backfill completa la historia que falte."""

    async def test_backfills_when_history_starts_later(self, env, gateway):
        walmex = await env.instrument(tracked_since=WED)
        gateway.closes["WALMEX*"] = routed(D, "WALMEX*", closes((WED, "54.1")))
        await env.price_sync.sync(walmex, WED, FRI)
        await env.instruments.track_since(walmex.id, MON)

        gateway.closes["WALMEX*"] = routed(
            D, "WALMEX*", closes((MON, "53.9"), (WED, "54.1"))
        )
        handler = TrackInstrumentHandler(
            instrument_repository=env.instruments,
            price_repository=env.prices,
            price_sync=env.price_sync,
            uow=env.uow,
        )
        result = await handler.handle(
            TrackInstrumentCommand(instrument_id=walmex.id, since=MON, as_of=FRI)
        )
        assert result.started is False
        assert result.sync is not None
        assert gateway.calls[-1].start == subtract_business_days(MON, 5)
        assert MON in await env.saved(walmex)


class TestTrackInstrument:
    def handler(self, env):
        return TrackInstrumentHandler(
            instrument_repository=env.instruments,
            price_repository=env.prices,
            price_sync=env.price_sync,
            uow=env.uow,
        )

    async def test_starts_tracking_and_backfills(self, env, gateway):
        walmex = await env.instrument(tracked_since=None)
        gateway.closes["WALMEX*"] = routed(
            D, "WALMEX*", closes((date(2026, 11, 2), "53"), (MON, "54.1"))
        )

        result = await self.handler(env).handle(
            TrackInstrumentCommand(instrument_id=walmex.id, since=MON, as_of=FRI)
        )

        assert result.started is True
        assert result.sync is not None and result.sync.saved == 2
        assert (await env.instruments.get_by_id(walmex.id)).tracked_since == MON
        assert gateway.calls[0].start == subtract_business_days(MON, 5)

    async def test_already_tracked_with_prices_does_nothing(self, env, gateway):
        walmex = await env.instrument(tracked_since=MON)
        gateway.closes["WALMEX*"] = routed(D, "WALMEX*", closes((MON, "54.1")))
        await env.price_sync.sync(walmex, MON, FRI)

        result = await self.handler(env).handle(
            TrackInstrumentCommand(instrument_id=walmex.id, since=WED, as_of=FRI)
        )
        assert (result.started, result.sync) == (False, None)
        assert len(gateway.calls) == 1

    async def test_earlier_date_extends_the_history(self, env, gateway):
        walmex = await env.instrument(tracked_since=WED)
        gateway.closes["WALMEX*"] = routed(D, "WALMEX*", closes((MON, "54.1")))
        result = await self.handler(env).handle(
            TrackInstrumentCommand(instrument_id=walmex.id, since=MON, as_of=FRI)
        )
        assert result.started is True
        assert (await env.instruments.get_by_id(walmex.id)).tracked_since == MON

    async def test_provider_failure_keeps_tracking_for_the_job(self, env, gateway):
        walmex = await env.instrument(tracked_since=None)
        result = await self.handler(env).handle(
            TrackInstrumentCommand(instrument_id=walmex.id, since=MON, as_of=FRI)
        )
        assert result.error is not None
        assert (await env.instruments.get_by_id(walmex.id)).tracked_since == MON


def listing(symbol, name, *, market=Market.BMV, kind=InstrumentType.STOCK, active=True):
    return InstrumentListing(
        market=market,
        symbol=symbol,
        name=name,
        instrument_type=kind,
        currency="USD" if market is Market.US else "MXN",
        isin="MX01WA000038" if symbol == "WALMEX*" else None,
        exchange="BMV",
        is_active=active,
    )


class TestCatalog:
    async def test_creates_and_updates_without_touching_app_fields(self, env, gateway):
        walmex = await env.instrument(name="Walmex viejo", preferred="databursatil")
        gateway.catalogs[Market.BMV] = [
            listing("WALMEX*", "WAL - MART DE MEXICO"),
            listing("FUNO11", "FIBRA UNO", kind=InstrumentType.FIBRA),
            listing("AA1CK", "CKD", kind=InstrumentType.OTHER, active=False),
        ]
        handler = SyncInstrumentCatalogHandler(
            instrument_repository=env.instruments, gateway=gateway, uow=env.uow
        )

        stats = await handler.handle(SyncInstrumentCatalogCommand(market=Market.BMV))

        assert (stats.received, stats.created, stats.updated) == (3, 2, 1)
        updated = await env.instruments.get_by_id(walmex.id)
        assert updated.name == "WAL - MART DE MEXICO"
        assert updated.isin == "MX01WA000038"
        assert updated.preferred_provider == "databursatil"
        assert updated.tracked_since == MON
        assert await env.instruments.count_by_market(Market.BMV) == 3

        again = await handler.handle(SyncInstrumentCatalogCommand(market=Market.BMV))
        assert (again.created, again.updated) == (0, 0)


class TestSearch:
    def handler(self, env):
        return SearchInstrumentsHandler(
            instrument_repository=env.instruments, gateway=env.gateway, uow=env.uow
        )

    async def test_downloads_empty_catalogs_once(self, env, gateway):
        gateway.catalogs[Market.BMV] = [
            listing("WALMEX*", "WAL - MART DE MEXICO"),
            listing("WALMEXV", "OTRA SERIE", active=False),
        ]
        gateway.catalogs[Market.SIC] = [listing("AAPL*", "APPLE", market=Market.SIC)]

        results = await self.handler(env).handle(SearchInstrumentsQuery("walmex"))

        assert [r.symbol for r in results] == ["WALMEX*", "WALMEXV"]
        assert set(gateway.catalog_calls) == {Market.BMV, Market.SIC}
        await self.handler(env).handle(SearchInstrumentsQuery("walmex"))
        assert len(gateway.catalog_calls) == 2

    async def test_orders_exact_then_prefix_then_name(self, env, gateway):
        await env.instrument("AC*", name="ARCA CONTINENTAL", tracked_since=None)
        await env.instrument("ACCELSA", name="ACCEL", tracked_since=None)
        await env.instrument("KOF", name="COCA-COLA FEMSA (no AC)", tracked_since=None)
        gateway.catalogs[Market.SIC] = [listing("X*", "X", market=Market.SIC)]

        results = await self.handler(env).handle(
            SearchInstrumentsQuery("ac", market=Market.BMV)
        )
        assert [r.symbol for r in results] == ["AC*", "ACCELSA", "KOF"]

    async def test_escapes_like_wildcards(self, env, gateway):
        await env.instrument("WALMEX*", tracked_since=None)
        results = await self.handler(env).handle(
            SearchInstrumentsQuery("%", market=Market.BMV)
        )
        assert results == []

    async def test_us_symbol_missing_asks_the_provider(self, env, gateway):
        gateway.search_results["MSFT"] = [
            listing("MSFT", "Microsoft Corporation", market=Market.US),
            listing("MSFU", "Direxion MSFT ETF", market=Market.US, kind=InstrumentType.ETF),
        ]
        results = await self.handler(env).handle(
            SearchInstrumentsQuery("msft", market=Market.US)
        )
        assert [r.symbol for r in results] == ["MSFT", "MSFU"]
        assert results[0].currency == "USD"

        # Ya está: no se vuelve a preguntar.
        await self.handler(env).handle(SearchInstrumentsQuery("MSFT", market=Market.US))
        assert gateway.search_calls == ["msft"]

    async def test_provider_down_returns_what_is_stored(self, env, gateway):
        await env.instrument("AAPL", market=Market.US, currency="USD", name="Apple")
        gateway.search_error = NoProviderAvailable("búsqueda", [])
        results = await self.handler(env).handle(
            SearchInstrumentsQuery("apple", market=Market.US)
        )
        assert [r.symbol for r in results] == ["AAPL"]

    async def test_catalog_down_still_answers(self, env, gateway):
        gateway.catalogs[Market.BMV] = NoProviderAvailable("catálogo BMV", [])
        results = await self.handler(env).handle(
            SearchInstrumentsQuery("walmex", market=Market.BMV)
        )
        assert results == []
