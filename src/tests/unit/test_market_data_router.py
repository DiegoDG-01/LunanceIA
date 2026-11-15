"""Router de precios: orden por mercado, proveedor fijo, respaldo, cuotas y salud en Redis."""

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from fakeredis import FakeAsyncRedis
from pydantic import SecretStr
from redis.exceptions import ConnectionError as RedisConnectionError

from application.interfaces.market_data import (
    DailyClose,
    FxRate,
    FxRateProvider,
    InstrumentCatalogSource,
    InstrumentListing,
    InstrumentSearchSource,
    MarketDataProvider,
    NoProviderAvailable,
    ProviderName,
    ProviderUnavailable,
    QuotaExhausted,
    SymbolNotSupported,
)
from domain.objects.enums import InstrumentType, Market
from infrastructure.config.settings import settings
from infrastructure.external_services.market_data.factory import (
    build_market_data_router,
    parse_routes,
)
from infrastructure.external_services.market_data.quotas import (
    ProviderHealth,
    ProviderQuotas,
)
from infrastructure.external_services.market_data.router import MarketDataRouter
from infrastructure.rate_limiting.limiters import RateLimitRule, RedisRateLimiter

D = ProviderName.DATABURSATIL
E = ProviderName.EODHD
T = ProviderName.TWELVEDATA
START = date(2026, 11, 2)
END = date(2026, 11, 13)
CLOSE = [DailyClose(price_date=END, close=Decimal("54.79"))]


class FakeProvider(MarketDataProvider):
    def __init__(self, name, markets, *outcomes):
        self.name = name
        self.markets = frozenset(markets)
        # Un resultado por llamada (el último se repite): cierres o una excepción a lanzar.
        self.outcomes = list(outcomes) or [CLOSE]
        self.calls: list[str] = []

    def provider_symbol(self, market, symbol):
        return f"{symbol}@{self.name.value}"

    async def fetch_daily_closes(self, provider_symbol, start, end):
        self.calls.append(provider_symbol)
        outcome = self.outcomes[min(len(self.calls), len(self.outcomes)) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeFx(FxRateProvider):
    name = ProviderName.BANXICO

    def __init__(self, outcome=None):
        self.outcome = outcome
        self.calls = 0

    def supports(self, base, quote):
        return (base, quote) == ("USD", "MXN")

    async def fetch_rates(self, base, quote, start, end):
        self.calls += 1
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return [FxRate(rate_date=END, rate=Decimal("18.5525"))]


class Clock:
    def __init__(self, now=1_000_000.0):
        self.now = now

    def __call__(self):
        return self.now


@pytest.fixture
def redis():
    return FakeAsyncRedis(decode_responses=True)


@pytest.fixture
def clock():
    return Clock()


def make_router(
    redis,
    clock,
    providers,
    routes=None,
    *,
    fx=(),
    rules=None,
    max_wait=65,
    sleeps=None,
):
    async def fake_sleep(seconds):
        if sleeps is not None:
            sleeps.append(seconds)
        clock.now += seconds

    return MarketDataRouter(
        providers={p.name: p for p in providers},
        routes=routes or {Market.BMV: (D, E), Market.US: (T, E)},
        fx_providers=fx,
        quotas=ProviderQuotas(
            RedisRateLimiter(lambda: redis, prefix="md", clock=clock),
            rules if rules is not None else {},
        ),
        health=ProviderHealth(lambda: redis),
        max_quota_wait=max_wait,
        sleep=fake_sleep,
    )


class TestRouting:
    async def test_first_provider_of_the_route_answers(self, redis, clock):
        d, e = FakeProvider(D, {Market.BMV}), FakeProvider(E, {Market.BMV})
        router = make_router(redis, clock, [d, e])

        result = await router.fetch_daily_closes(Market.BMV, "WALMEX*", START, END)

        assert result.provider is D
        assert result.provider_symbol == "WALMEX*@databursatil"
        assert result.closes == CLOSE
        assert e.calls == []

    async def test_preferred_provider_goes_first(self, redis, clock):
        d, e = FakeProvider(D, {Market.BMV}), FakeProvider(E, {Market.BMV})
        router = make_router(redis, clock, [d, e])

        result = await router.fetch_daily_closes(
            Market.BMV, "WALMEX*", START, END, preferred=E
        )

        assert result.provider is E
        assert d.calls == []

    async def test_preferred_outside_the_route_is_ignored(self, redis, clock):
        d = FakeProvider(D, {Market.BMV})
        router = make_router(redis, clock, [d], {Market.BMV: (D,)})
        result = await router.fetch_daily_closes(
            Market.BMV, "WALMEX*", START, END, preferred=T
        )
        assert result.provider is D

    async def test_saved_provider_symbol_wins(self, redis, clock):
        d = FakeProvider(D, {Market.BMV})
        router = make_router(redis, clock, [d], {Market.BMV: (D,)})
        result = await router.fetch_daily_closes(
            Market.BMV, "GFNORTE", START, END, provider_symbols={D: "GFNORTEO"}
        )
        assert d.calls == ["GFNORTEO"]
        assert result.provider_symbol == "GFNORTEO"

    async def test_empty_answer_is_a_valid_answer(self, redis, clock):
        d, e = FakeProvider(D, {Market.BMV}, []), FakeProvider(E, {Market.BMV})
        router = make_router(redis, clock, [d, e])
        result = await router.fetch_daily_closes(Market.BMV, "WALMEX*", START, END)
        assert result.provider is D
        assert result.closes == []
        assert e.calls == []

    def test_routes_drop_providers_not_configured_or_not_covering_the_market(
        self, redis, clock
    ):
        t, e = FakeProvider(T, {Market.US}), FakeProvider(E, {Market.BMV, Market.US})
        router = make_router(
            redis,
            clock,
            [t, e],
            {Market.BMV: (T, D, E, E), Market.US: (T, E)},
        )
        assert router.providers_for(Market.BMV) == (E,)
        assert router.providers_for(Market.US) == (T, E)
        assert router.providers_for(Market.SIC) == ()


class TestFallback:
    async def test_unavailable_provider_falls_back_and_is_marked_down(
        self, redis, clock
    ):
        d = FakeProvider(D, {Market.BMV}, ProviderUnavailable(D, "HTTP 503"))
        e = FakeProvider(E, {Market.BMV})
        router = make_router(redis, clock, [d, e])

        result = await router.fetch_daily_closes(Market.BMV, "WALMEX*", START, END)

        assert result.provider is E
        assert [a.outcome for a in result.attempts] == ["unavailable"]
        assert await redis.exists("md_down:databursatil")
        assert 0 < await redis.ttl("md_down:databursatil") <= 900

        # La siguiente petición ni lo intenta.
        await router.fetch_daily_closes(Market.BMV, "FUNO11", START, END)
        assert len(d.calls) == 1

    async def test_unsupported_symbol_is_reported_and_not_marked_down(
        self, redis, clock
    ):
        d = FakeProvider(D, {Market.BMV}, SymbolNotSupported(D, "desconocida"))
        e = FakeProvider(E, {Market.BMV})
        router = make_router(redis, clock, [d, e])

        result = await router.fetch_daily_closes(Market.BMV, "ZZZ*", START, END)

        assert result.provider is E
        assert result.unsupported == (D,)
        assert not await redis.exists("md_down:databursatil")

    async def test_skip_avoids_known_unsupported_providers(self, redis, clock):
        d, e = FakeProvider(D, {Market.BMV}), FakeProvider(E, {Market.BMV})
        router = make_router(redis, clock, [d, e])
        result = await router.fetch_daily_closes(
            Market.BMV, "WALMEX*", START, END, skip=frozenset({D})
        )
        assert result.provider is E
        assert d.calls == []

    async def test_remote_quota_marks_down_for_retry_after(self, redis, clock):
        e = FakeProvider(
            E, {Market.US}, QuotaExhausted(E, "cuota diaria", retry_after=7200)
        )
        t = FakeProvider(T, {Market.US})
        router = make_router(redis, clock, [t, e], {Market.US: (E, T)})

        result = await router.fetch_daily_closes(Market.US, "AAPL", START, END)

        assert result.provider is T
        assert 3600 < await redis.ttl("md_down:eodhd") <= 7200

    async def test_unexpected_error_does_not_stop_the_route(self, redis, clock):
        d = FakeProvider(D, {Market.BMV}, KeyError("precio"))
        e = FakeProvider(E, {Market.BMV})
        router = make_router(redis, clock, [d, e])
        result = await router.fetch_daily_closes(Market.BMV, "WALMEX*", START, END)
        assert result.provider is E
        assert result.attempts[0].detail == "KeyError"

    async def test_all_fail(self, redis, clock):
        d = FakeProvider(D, {Market.BMV}, ProviderUnavailable(D, "timeout"))
        e = FakeProvider(E, {Market.BMV}, SymbolNotSupported(E, "404"))
        router = make_router(redis, clock, [d, e])

        with pytest.raises(NoProviderAvailable) as caught:
            await router.fetch_daily_closes(Market.BMV, "WALMEX*", START, END)

        assert [(a.provider, a.outcome) for a in caught.value.attempts] == [
            (D, "unavailable"),
            (E, "unsupported"),
        ]
        assert "BMV:WALMEX*" in str(caught.value)

    async def test_market_without_providers(self, redis, clock):
        router = make_router(redis, clock, [])
        with pytest.raises(NoProviderAvailable, match="sin proveedores"):
            await router.fetch_daily_closes(Market.SIC, "AAPL*", START, END)


class TestQuotas:
    async def test_local_quota_moves_to_the_next_provider(self, redis, clock):
        e, t = FakeProvider(E, {Market.US}), FakeProvider(T, {Market.US})
        router = make_router(
            redis,
            clock,
            [e, t],
            {Market.US: (E, T)},
            rules={E: (RateLimitRule(limit=1, window_seconds=86400),)},
        )

        first = await router.fetch_daily_closes(Market.US, "AAPL", START, END)
        second = await router.fetch_daily_closes(Market.US, "MSFT", START, END)

        assert first.provider is E
        assert second.provider is T
        assert second.attempts[0].outcome == "quota"
        assert len(e.calls) == 1

    async def test_short_wait_is_cheaper_than_falling_back(self, redis, clock):
        t, e = FakeProvider(T, {Market.US}), FakeProvider(E, {Market.US})
        sleeps: list[float] = []
        router = make_router(
            redis,
            clock,
            [t, e],
            rules={T: (RateLimitRule(limit=1, window_seconds=60),)},
            sleeps=sleeps,
        )

        await router.fetch_daily_closes(Market.US, "AAPL", START, END)
        result = await router.fetch_daily_closes(Market.US, "MSFT", START, END)

        assert result.provider is T
        assert len(sleeps) == 1 and 0 < sleeps[0] <= 60
        assert e.calls == []

    async def test_minute_window_full_does_not_spend_the_daily_one(self, redis, clock):
        limiter = RedisRateLimiter(lambda: redis, prefix="md", clock=clock)
        quotas = ProviderQuotas(
            limiter,
            {
                T: (
                    RateLimitRule(limit=100, window_seconds=86400),
                    RateLimitRule(limit=1, window_seconds=60),
                )
            },
        )
        await quotas.reserve(T)
        with pytest.raises(QuotaExhausted):
            await quotas.reserve(T)
        daily = await redis.keys("md:100/86400:*")
        assert len(daily) == 1
        assert await redis.get(daily[0]) == "1"

    async def test_redis_down_does_not_stop_calls(self, clock):
        class BrokenRedis:
            def pipeline(self, transaction=True):
                raise RedisConnectionError("down")

            async def exists(self, *_):
                raise RedisConnectionError("down")

            async def set(self, *_, **__):
                raise RedisConnectionError("down")

        broken: Any = BrokenRedis()
        d = FakeProvider(D, {Market.BMV}, ProviderUnavailable(D, "503"))
        e = FakeProvider(E, {Market.BMV})
        router = make_router(
            broken,
            clock,
            [d, e],
            rules={E: (RateLimitRule(limit=1, window_seconds=60),)},
        )

        result = await router.fetch_daily_closes(Market.BMV, "WALMEX*", START, END)
        assert result.provider is E


class TestFx:
    async def test_banxico_answers(self, redis, clock):
        fx = FakeFx()
        router = make_router(redis, clock, [], fx=[fx])
        result = await router.fetch_fx_rates("USD", "MXN", START, END)
        assert result.provider is ProviderName.BANXICO
        assert result.rates[0].rate == Decimal("18.5525")

    async def test_unsupported_pair(self, redis, clock):
        fx = FakeFx()
        router = make_router(redis, clock, [], fx=[fx])
        with pytest.raises(NoProviderAvailable):
            await router.fetch_fx_rates("EUR", "MXN", START, END)
        assert fx.calls == 0

    async def test_banxico_down(self, redis, clock):
        fx = FakeFx(ProviderUnavailable(ProviderName.BANXICO, "Token inválido"))
        router = make_router(redis, clock, [], fx=[fx])
        with pytest.raises(NoProviderAvailable) as caught:
            await router.fetch_fx_rates("USD", "MXN", START, END)
        assert caught.value.attempts[0].outcome == "unavailable"
        assert await redis.exists("md_down:banxico")


class TestFactory:
    def test_parse_default_routes(self):
        routes = parse_routes(settings.model_fields["MARKET_DATA_ROUTES"].default)
        assert routes == {
            Market.BMV: (D, E),
            Market.SIC: (D, E),
            Market.US: (T, E),
        }

    def test_parse_is_lenient_with_spaces_case_and_duplicates(self):
        assert parse_routes(" bmv = DataBursatil , eodhd, eodhd ; ") == {
            Market.BMV: (D, E)
        }

    @pytest.mark.parametrize(
        "text",
        ["BMV", "XETRA=eodhd", "BMV=itick", "US=banxico"],
    )
    def test_parse_rejects(self, text):
        with pytest.raises(ValueError, match="MARKET_DATA_ROUTES"):
            parse_routes(text)

    def _settings(self, **overrides):
        values = {
            "DATABURSATIL_TOKEN": SecretStr(""),
            "EODHD_API_KEY": SecretStr(""),
            "TWELVEDATA_API_KEY": SecretStr(""),
            "BANXICO_TOKEN": SecretStr(""),
            "MARKET_DATA_ENABLE_YAHOO": False,
            "MARKET_DATA_ROUTES": settings.model_fields["MARKET_DATA_ROUTES"].default,
        }
        values.update(overrides)
        return settings.model_copy(update=values)

    def test_only_providers_with_keys_enter_the_routes(self, redis):
        router = build_market_data_router(
            self._settings(EODHD_API_KEY=SecretStr("k")), redis=lambda: redis
        )
        assert router.providers_for(Market.BMV) == (E,)
        assert router.providers_for(Market.US) == (E,)

    def test_all_keys(self, redis):
        router = build_market_data_router(
            self._settings(
                DATABURSATIL_TOKEN=SecretStr("a"),
                EODHD_API_KEY=SecretStr("b"),
                TWELVEDATA_API_KEY=SecretStr("c"),
                BANXICO_TOKEN=SecretStr("d"),
            ),
            redis=lambda: redis,
        )
        assert router.providers_for(Market.SIC) == (D, E)
        assert router.providers_for(Market.US) == (T, E)

    def test_yahoo_goes_last_only_when_enabled(self, redis):
        off = build_market_data_router(
            self._settings(MARKET_DATA_ROUTES="US=yahoo,eodhd"), redis=lambda: redis
        )
        assert off.providers_for(Market.US) == ()

        on = build_market_data_router(
            self._settings(EODHD_API_KEY=SecretStr("b"), MARKET_DATA_ENABLE_YAHOO=True),
            redis=lambda: redis,
        )
        assert on.providers_for(Market.BMV) == (E, ProviderName.YAHOO)
        assert on.providers_for(Market.US) == (E, ProviderName.YAHOO)


class FakeCatalogProvider(FakeProvider, InstrumentCatalogSource):
    catalog_markets = frozenset({Market.BMV})

    def __init__(self, *outcomes, catalog=None):
        super().__init__(D, {Market.BMV}, *outcomes)
        self.catalog = catalog

    async def fetch_catalog(self, market):
        if isinstance(self.catalog, Exception):
            raise self.catalog
        return self.catalog or []


class FakeSearchProvider(FakeProvider, InstrumentSearchSource):
    search_markets = frozenset({Market.US})

    def __init__(self, results=None):
        super().__init__(T, {Market.US})
        self.results = results

    async def search(self, query, market):
        if isinstance(self.results, Exception):
            raise self.results
        return self.results or []


LISTING = InstrumentListing(
    market=Market.BMV,
    symbol="WALMEX*",
    name="WAL - MART",
    instrument_type=InstrumentType.STOCK,
    currency="MXN",
)


class TestCatalogAndSearch:
    async def test_catalog_from_the_provider_that_has_it(self, redis, clock):
        router = make_router(redis, clock, [FakeCatalogProvider(catalog=[LISTING])])
        assert router.has_catalog(Market.BMV)
        assert not router.has_catalog(Market.US)
        assert await router.fetch_catalog(Market.BMV) == [LISTING]

    async def test_catalog_unavailable(self, redis, clock):
        router = make_router(
            redis,
            clock,
            [FakeCatalogProvider(catalog=ProviderUnavailable(D, "HTTP 503"))],
        )
        with pytest.raises(NoProviderAvailable):
            await router.fetch_catalog(Market.BMV)
        assert await redis.exists("md_down:databursatil")

    async def test_search_uses_quota_and_reports_failures(self, redis, clock):
        router = make_router(
            redis,
            clock,
            [FakeSearchProvider([LISTING])],
            rules={T: (RateLimitRule(limit=1, window_seconds=86400),)},
        )
        assert await router.search_instruments(Market.US, "aapl") == [LISTING]
        with pytest.raises(NoProviderAvailable) as caught:
            await router.search_instruments(Market.US, "msft")
        assert caught.value.attempts[0].outcome == "quota"

    async def test_attempts_carry_the_symbol_that_was_asked(self, redis, clock):
        d = FakeProvider(D, {Market.BMV}, SymbolNotSupported(D, "desconocida"))
        e = FakeProvider(E, {Market.BMV})
        router = make_router(redis, clock, [d, e])
        result = await router.fetch_daily_closes(
            Market.BMV, "WALMEX*", START, END, provider_symbols={D: "WALMEX*"}
        )
        assert result.attempts[0].provider_symbol == "WALMEX*"
