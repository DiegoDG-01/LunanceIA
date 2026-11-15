"""Router de proveedores de precios.

Por cada mercado hay una ruta ordenada (settings `MARKET_DATA_ROUTES`). El valor tiene un
proveedor fijo (`preferred`): se le pregunta primero y los demás solo entran si falla, para
no mezclar fuentes que difieren en días sueltos. Antes de cada llamada se reserva cuota; un
proveedor que falla queda marcado como caído un rato y la siguiente petición lo salta.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import replace
from datetime import date

from application.interfaces.market_data import (
    FxRateProvider,
    InstrumentCatalogSource,
    InstrumentListing,
    InstrumentSearchSource,
    MarketDataError,
    MarketDataGateway,
    MarketDataProvider,
    NoProviderAvailable,
    ProviderAttempt,
    ProviderName,
    QuotaExhausted,
    RoutedCloses,
    RoutedRates,
    SymbolNotSupported,
)
from domain.objects.enums import Market
from infrastructure.external_services.market_data.quotas import (
    ProviderHealth,
    ProviderQuotas,
)

logger = logging.getLogger(__name__)

# Twelve Data da 8 llamadas por minuto: esperar a la siguiente ventana sale más barato que
# gastar una de las 20 diarias de EODHD.
DEFAULT_MAX_QUOTA_WAIT = 65


class _Unsupported(Exception):
    pass


class MarketDataRouter(MarketDataGateway):
    def __init__(
        self,
        *,
        providers: Mapping[ProviderName, MarketDataProvider],
        routes: Mapping[Market, Sequence[ProviderName]],
        fx_providers: Sequence[FxRateProvider] = (),
        quotas: ProviderQuotas,
        health: ProviderHealth,
        max_quota_wait: int = DEFAULT_MAX_QUOTA_WAIT,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._providers = dict(providers)
        self._routes: dict[Market, tuple[ProviderName, ...]] = {}
        for market, names in routes.items():
            usable = []
            for name in names:
                provider = self._providers.get(name)
                if provider is None:
                    logger.info(
                        "Market data provider not configured; skipped",
                        extra={"provider": name.value, "market": market.value},
                    )
                elif market not in provider.markets:
                    logger.warning(
                        "Market data provider does not cover market; skipped",
                        extra={"provider": name.value, "market": market.value},
                    )
                elif name not in usable:
                    usable.append(name)
            self._routes[market] = tuple(usable)
        self._fx_providers = tuple(fx_providers)
        # Catálogo y búsqueda: los proveedores de precios que además los ofrecen.
        self._catalog_sources = [
            p
            for p in self._providers.values()
            if isinstance(p, InstrumentCatalogSource)
        ]
        self._search_sources = [
            p for p in self._providers.values() if isinstance(p, InstrumentSearchSource)
        ]
        self._quotas = quotas
        self._health = health
        self._max_quota_wait = max_quota_wait
        self._sleep = sleep

    def providers_for(self, market: Market) -> tuple[ProviderName, ...]:
        return self._routes.get(market, ())

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
        order = list(self.providers_for(market))
        if preferred in order:
            order.remove(preferred)
            order.insert(0, preferred)
        attempts: list[ProviderAttempt] = []
        unsupported: list[ProviderName] = []
        for name in order:
            provider = self._providers[name]
            provider_symbol = (provider_symbols or {}).get(
                name
            ) or provider.provider_symbol(market, symbol)
            if name in skip:
                attempts.append(
                    ProviderAttempt(
                        name, "unsupported", "marcado antes", provider_symbol
                    )
                )
                continue
            first_new = len(attempts)
            try:
                closes = await self._attempt(
                    name,
                    lambda p=provider, s=provider_symbol: p.fetch_daily_closes(
                        s, start, end
                    ),
                    attempts,
                )
            except _Unsupported:
                unsupported.append(name)
                continue
            finally:
                for i in range(first_new, len(attempts)):
                    attempts[i] = replace(attempts[i], provider_symbol=provider_symbol)
            if closes is None:
                continue
            return RoutedCloses(
                provider=name,
                provider_symbol=provider_symbol,
                closes=closes,
                unsupported=tuple(unsupported),
                attempts=tuple(attempts),
            )
        raise NoProviderAvailable(f"{market.value}:{symbol}", attempts)

    async def fetch_fx_rates(
        self, base: str, quote: str, start: date, end: date
    ) -> RoutedRates:
        attempts: list[ProviderAttempt] = []
        for provider in self._fx_providers:
            if not provider.supports(base, quote):
                continue
            try:
                rates = await self._attempt(
                    provider.name,
                    lambda p=provider: p.fetch_rates(base, quote, start, end),
                    attempts,
                )
            except _Unsupported:
                continue
            if rates is not None:
                return RoutedRates(provider=provider.name, rates=rates)
        raise NoProviderAvailable(f"{base}/{quote}", attempts)

    def has_catalog(self, market: Market) -> bool:
        return any(market in s.catalog_markets for s in self._catalog_sources)

    async def fetch_catalog(self, market: Market) -> list[InstrumentListing]:
        attempts: list[ProviderAttempt] = []
        for source in self._catalog_sources:
            if market not in source.catalog_markets:
                continue
            try:
                listings = await self._attempt(
                    source.name,
                    lambda s=source: s.fetch_catalog(market),
                    attempts,
                )
            except _Unsupported:
                continue
            if listings is not None:
                return listings
        raise NoProviderAvailable(f"catálogo {market.value}", attempts)

    async def search_instruments(
        self, market: Market, query: str
    ) -> list[InstrumentListing]:
        attempts: list[ProviderAttempt] = []
        for source in self._search_sources:
            if market not in source.search_markets:
                continue
            try:
                listings = await self._attempt(
                    source.name,
                    lambda s=source: s.search(query, market),
                    attempts,
                )
            except _Unsupported:
                continue
            if listings is not None:
                return listings
        raise NoProviderAvailable(f"búsqueda {market.value}:{query}", attempts)

    async def _attempt(self, name, call, attempts: list[ProviderAttempt]):
        """Resultado de la llamada, o None si hay que pasar al siguiente. Lanza `_Unsupported`
        si el proveedor no tiene el símbolo."""
        if await self._health.is_down(name):
            attempts.append(ProviderAttempt(name, "down"))
            return None
        try:
            await self._reserve(name)
        except QuotaExhausted as error:
            attempts.append(ProviderAttempt(name, "quota", error.detail))
            return None
        try:
            return await call()
        except SymbolNotSupported as error:
            attempts.append(ProviderAttempt(name, "unsupported", error.detail))
            raise _Unsupported from None
        except QuotaExhausted as error:
            attempts.append(ProviderAttempt(name, "quota", error.detail))
            await self._health.mark_down(name, error.retry_after, reason="quota")
        except MarketDataError as error:
            attempts.append(ProviderAttempt(name, "unavailable", error.detail))
            await self._health.mark_down(name, reason="unavailable")
        # Un formato nuevo o un dato raro de un proveedor no debe tumbar el job.
        except Exception as error:
            logger.exception(
                "Market data provider failed unexpectedly",
                extra={"provider": name.value},
            )
            attempts.append(ProviderAttempt(name, "unavailable", type(error).__name__))
            await self._health.mark_down(name, reason="error")
        logger.warning(
            "Market data provider failed; trying next",
            extra={"provider": name.value, "outcome": attempts[-1].outcome},
        )
        return None

    async def _reserve(self, name: ProviderName) -> None:
        try:
            await self._quotas.reserve(name)
        except QuotaExhausted as error:
            if error.retry_after > self._max_quota_wait:
                raise
            await self._sleep(error.retry_after)
            await self._quotas.reserve(name)
