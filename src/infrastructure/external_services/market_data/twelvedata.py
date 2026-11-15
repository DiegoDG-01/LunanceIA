"""Twelve Data (https://twelvedata.com/docs#time-series): EE. UU. y tipo de cambio.

El plan gratis no cubre la BMV (404 «available starting with the Pro plan»). Los errores
llegan con `status: "error"` y un `code` que repite el HTTP. `end_date` es exclusivo: se pide
un día más y se filtra. Un rango sin días hábiles responde 400 «No data is available».
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import NoReturn

import httpx

from application.interfaces.market_data import (
    DailyClose,
    InstrumentListing,
    InstrumentSearchSource,
    MarketDataProvider,
    ProviderName,
    ProviderUnavailable,
    QuotaExhausted,
    SymbolNotSupported,
)
from domain.objects.enums import InstrumentType, Market
from infrastructure.external_services.market_data.provider_http import (
    ProviderHttp,
    seconds_until_utc_midnight,
)

_TYPES = {
    "common stock": InstrumentType.STOCK,
    "etf": InstrumentType.ETF,
}


class TwelveDataProvider(MarketDataProvider, InstrumentSearchSource):
    name = ProviderName.TWELVEDATA
    markets = frozenset({Market.US})
    search_markets = frozenset({Market.US})
    URL = "https://api.twelvedata.com/time_series"
    SEARCH_URL = "https://api.twelvedata.com/symbol_search"

    def __init__(
        self, *, api_key: str, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        if not api_key:
            raise ValueError("TwelveDataProvider necesita TWELVEDATA_API_KEY")
        self._api_key = api_key
        self._http = ProviderHttp(self.name, secret=api_key, transport=transport)

    def provider_symbol(self, market: Market, symbol: str) -> str:
        return symbol

    async def fetch_daily_closes(
        self, provider_symbol: str, start: date, end: date
    ) -> list[DailyClose]:
        response = await self._http.get(
            self.URL,
            params={
                "symbol": provider_symbol,
                "interval": "1day",
                "start_date": start.isoformat(),
                "end_date": (end + timedelta(days=1)).isoformat(),
                "order": "asc",
                "outputsize": 5000,
                "apikey": self._api_key,
            },
        )
        data = self._http.json(response)
        if not isinstance(data, dict):
            raise ProviderUnavailable(self.name, "respuesta inesperada")
        if data.get("status") != "ok":
            if _is_empty_range(data):
                return []
            self._raise_error(provider_symbol, response, data)
        closes = [
            DailyClose(
                price_date=date.fromisoformat(row["datetime"][:10]),
                close=Decimal(str(row["close"])),
            )
            for row in data.get("values") or []
            if row.get("close") is not None
        ]
        closes.sort(key=lambda c: c.price_date)
        return [c for c in closes if start <= c.price_date <= end]

    async def search(self, query: str, market: Market) -> list[InstrumentListing]:
        """Valores de EE. UU. que coinciden con `query` (símbolo o nombre). La búsqueda
        devuelve el mismo símbolo en varias bolsas del mundo: se queda con el listado de
        EE. UU. en dólares."""
        if market is not Market.US:
            return []
        response = await self._http.get(
            self.SEARCH_URL,
            params={"symbol": query, "outputsize": 30, "apikey": self._api_key},
        )
        data = self._http.json(response)
        if not isinstance(data, dict):
            raise ProviderUnavailable(self.name, "respuesta inesperada")
        if data.get("status") not in (None, "ok"):
            self._raise_error(query, response, data)
        listings: dict[str, InstrumentListing] = {}
        for row in data.get("data") or []:
            if not isinstance(row, dict):
                continue
            if row.get("country") != "United States" or row.get("currency") != "USD":
                continue
            symbol = str(row.get("symbol") or "").strip().upper()
            if not symbol or len(symbol) > 30 or symbol in listings:
                continue
            listings[symbol] = InstrumentListing(
                market=Market.US,
                symbol=symbol,
                name=str(row.get("instrument_name") or symbol).strip()[:255],
                instrument_type=_TYPES.get(
                    str(row.get("instrument_type") or "").lower(), InstrumentType.OTHER
                ),
                currency="USD",
                exchange=(str(row.get("exchange") or "").strip()[:60] or None),
            )
        return list(listings.values())

    def _raise_error(
        self, symbol: str, response: httpx.Response, data: dict
    ) -> NoReturn:
        code = data.get("code", response.status_code)
        message = str(data.get("message", ""))[:160]
        if code in (403, 404):
            raise SymbolNotSupported(self.name, f"{symbol}: {message}")
        if code == 429:
            # Twelve Data no separa la cuota por minuto de la diaria en el código.
            per_day = "day" in message.lower() or "daily" in message.lower()
            raise QuotaExhausted(
                self.name,
                message,
                retry_after=seconds_until_utc_midnight() if per_day else 60,
            )
        raise ProviderUnavailable(self.name, f"código {code}: {message}")


def _is_empty_range(data: dict) -> bool:
    return (
        data.get("code") == 400
        and "no data is available" in str(data.get("message", "")).lower()
    )
