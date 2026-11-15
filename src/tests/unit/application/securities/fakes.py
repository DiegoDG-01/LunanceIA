"""Gateway de precios en memoria para probar los casos de uso sin red."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from application.interfaces.market_data import (
    DailyClose,
    FxRate,
    InstrumentListing,
    MarketDataGateway,
    NoProviderAvailable,
    ProviderAttempt,
    ProviderName,
    RoutedCloses,
    RoutedRates,
)
from domain.objects.enums import Market


@dataclass
class Call:
    market: Market
    symbol: str
    start: date
    end: date
    preferred: ProviderName | None
    provider_symbols: dict
    skip: frozenset


@dataclass
class FakeGateway(MarketDataGateway):
    # Respuesta por símbolo: RoutedCloses, o una excepción.
    closes: dict = field(default_factory=dict)
    rates: list[FxRate] = field(default_factory=list)
    fx_error: Exception | None = None
    catalogs: dict = field(default_factory=dict)
    search_results: dict = field(default_factory=dict)
    search_error: Exception | None = None
    calls: list[Call] = field(default_factory=list)
    fx_calls: list[tuple[date, date]] = field(default_factory=list)
    catalog_calls: list[Market] = field(default_factory=list)
    search_calls: list[str] = field(default_factory=list)

    def providers_for(self, market: Market) -> tuple[ProviderName, ...]:
        return (ProviderName.DATABURSATIL, ProviderName.EODHD)

    async def fetch_daily_closes(
        self,
        market: Market,
        symbol: str,
        start: date,
        end: date,
        *,
        preferred: ProviderName | None = None,
        provider_symbols: Mapping[ProviderName, str] | None = None,
        skip: frozenset[ProviderName] = frozenset(),
    ) -> RoutedCloses:
        self.calls.append(
            Call(market, symbol, start, end, preferred, dict(provider_symbols or {}), skip)
        )
        answer = self.closes.get(symbol)
        if callable(answer):
            answer = answer(self.calls[-1])
        if isinstance(answer, Exception):
            raise answer
        if answer is None:
            raise NoProviderAvailable(f"{market.value}:{symbol}", [])
        return RoutedCloses(
            provider=answer.provider,
            provider_symbol=answer.provider_symbol,
            closes=[c for c in answer.closes if start <= c.price_date <= end],
            unsupported=answer.unsupported,
            attempts=answer.attempts,
        )

    async def fetch_fx_rates(
        self, base: str, quote: str, start: date, end: date
    ) -> RoutedRates:
        self.fx_calls.append((start, end))
        if self.fx_error:
            raise self.fx_error
        return RoutedRates(
            provider=ProviderName.BANXICO,
            rates=[r for r in self.rates if start <= r.rate_date <= end],
        )

    def has_catalog(self, market: Market) -> bool:
        return market in (Market.BMV, Market.SIC)

    async def fetch_catalog(self, market: Market) -> list[InstrumentListing]:
        self.catalog_calls.append(market)
        answer = self.catalogs.get(market)
        if isinstance(answer, Exception):
            raise answer
        return list(answer or [])

    async def search_instruments(
        self, market: Market, query: str
    ) -> list[InstrumentListing]:
        self.search_calls.append(query)
        if self.search_error:
            raise self.search_error
        return list(self.search_results.get(query.upper(), []))


def closes(*items: tuple[date, str], trading: bool = True) -> list[DailyClose]:
    return [
        DailyClose(price_date=d, close=Decimal(v), is_trading_day=trading)
        for d, v in items
    ]


def routed(
    provider: ProviderName,
    symbol: str,
    data: list[DailyClose],
    *,
    unsupported: tuple[ProviderName, ...] = (),
    attempts: tuple[ProviderAttempt, ...] = (),
) -> RoutedCloses:
    return RoutedCloses(
        provider=provider,
        provider_symbol=symbol,
        closes=data,
        unsupported=unsupported,
        attempts=attempts,
    )
