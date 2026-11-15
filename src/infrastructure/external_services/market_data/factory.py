from collections.abc import Callable
from functools import lru_cache

import httpx
from redis.asyncio import Redis

from application.interfaces.market_data import (
    FxRateProvider,
    MarketDataProvider,
    ProviderName,
)
from domain.objects.enums import Market
from infrastructure.cache.redis import get_redis
from infrastructure.config.settings import Settings, settings
from infrastructure.external_services.market_data.banxico import BanxicoFxProvider
from infrastructure.external_services.market_data.databursatil import (
    DataBursatilProvider,
)
from infrastructure.external_services.market_data.eodhd import EodhdProvider
from infrastructure.external_services.market_data.quotas import (
    ProviderHealth,
    ProviderQuotas,
)
from infrastructure.external_services.market_data.router import MarketDataRouter
from infrastructure.external_services.market_data.twelvedata import TwelveDataProvider
from infrastructure.external_services.market_data.yahoo import YahooProvider
from infrastructure.rate_limiting.limiters import RedisRateLimiter

PRICE_PROVIDERS = frozenset(
    {
        ProviderName.DATABURSATIL,
        ProviderName.EODHD,
        ProviderName.TWELVEDATA,
        ProviderName.YAHOO,
    }
)


def parse_routes(text: str) -> dict[Market, tuple[ProviderName, ...]]:
    """`BMV=databursatil,eodhd;US=twelvedata,eodhd` → {Market.BMV: (...), ...}."""
    routes: dict[Market, tuple[ProviderName, ...]] = {}
    for chunk in text.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        market_text, sep, names_text = chunk.partition("=")
        if not sep:
            raise ValueError(f"MARKET_DATA_ROUTES: falta '=' en {chunk!r}")
        try:
            market = Market(market_text.strip().upper())
        except ValueError:
            raise ValueError(
                f"MARKET_DATA_ROUTES: mercado desconocido {market_text.strip()!r}"
            ) from None
        names = []
        for raw in names_text.split(","):
            raw = raw.strip().lower()
            if not raw:
                continue
            try:
                name = ProviderName(raw)
            except ValueError:
                raise ValueError(
                    f"MARKET_DATA_ROUTES: proveedor desconocido {raw!r}"
                ) from None
            if name not in PRICE_PROVIDERS:
                raise ValueError(
                    f"MARKET_DATA_ROUTES: {raw!r} no da precios de valores"
                )
            if name not in names:
                names.append(name)
        routes[market] = tuple(names)
    return routes


def build_market_data_router(
    settings: Settings,
    *,
    redis: Callable[[], Redis] = get_redis,
    transport: httpx.AsyncBaseTransport | None = None,
) -> MarketDataRouter:
    """Solo entran los proveedores con llave; Yahoo, solo si está encendido."""
    providers: dict[ProviderName, MarketDataProvider] = {}
    if token := settings.DATABURSATIL_TOKEN.get_secret_value():
        providers[ProviderName.DATABURSATIL] = DataBursatilProvider(
            token=token, transport=transport
        )
    if key := settings.EODHD_API_KEY.get_secret_value():
        providers[ProviderName.EODHD] = EodhdProvider(api_key=key, transport=transport)
    if key := settings.TWELVEDATA_API_KEY.get_secret_value():
        providers[ProviderName.TWELVEDATA] = TwelveDataProvider(
            api_key=key, transport=transport
        )

    routes = parse_routes(settings.MARKET_DATA_ROUTES)
    if settings.MARKET_DATA_ENABLE_YAHOO:
        providers[ProviderName.YAHOO] = YahooProvider(transport=transport)
        routes = {
            market: names
            if ProviderName.YAHOO in names
            else (*names, ProviderName.YAHOO)
            for market, names in routes.items()
        }
    else:
        routes = {
            market: tuple(n for n in names if n is not ProviderName.YAHOO)
            for market, names in routes.items()
        }

    fx_providers: list[FxRateProvider] = []
    if token := settings.BANXICO_TOKEN.get_secret_value():
        fx_providers.append(BanxicoFxProvider(token=token, transport=transport))

    return MarketDataRouter(
        providers=providers,
        routes=routes,
        fx_providers=fx_providers,
        quotas=ProviderQuotas(RedisRateLimiter(redis, prefix="md")),
        health=ProviderHealth(redis),
    )


@lru_cache(maxsize=1)
def get_market_data_gateway() -> MarketDataRouter:
    """El router de la app, armado una vez con las settings. Redis se resuelve en cada
    llamada, así que se puede crear antes del `lifespan`."""
    return build_market_data_router(settings)
