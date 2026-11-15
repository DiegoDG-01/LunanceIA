"""EODHD (https://eodhd.com/financial-apis/api-for-historical-data-and-volumes): respaldo
para BMV, SIC y EE. UU.

El plan gratis da un año de historia y 20 llamadas al día. `close` es el cierre sin ajustar.
Símbolo desconocido: 404 «Ticker Not Found.». Cuota del día agotada: 402.
"""

from datetime import date
from decimal import Decimal

import httpx

from application.interfaces.market_data import (
    DailyClose,
    MarketDataProvider,
    ProviderName,
    ProviderUnavailable,
    QuotaExhausted,
    SymbolNotSupported,
)
from domain.objects.enums import Market
from infrastructure.external_services.market_data.provider_http import (
    ProviderHttp,
    seconds_until_utc_midnight,
)


class EodhdProvider(MarketDataProvider):
    name = ProviderName.EODHD
    markets = frozenset({Market.BMV, Market.SIC, Market.US})
    BASE_URL = "https://eodhd.com/api/eod"

    def __init__(
        self, *, api_key: str, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        if not api_key:
            raise ValueError("EodhdProvider necesita EODHD_API_KEY")
        self._api_key = api_key
        self._http = ProviderHttp(self.name, secret=api_key, transport=transport)

    def provider_symbol(self, market: Market, symbol: str) -> str:
        if market is Market.US:
            return f"{symbol.replace('.', '-')}.US"
        # La serie `*` de la BMV no va en el ticker de EODHD (`WALMEX*` → `WALMEX.MX`).
        return f"{symbol.rstrip('*')}.MX"

    async def fetch_daily_closes(
        self, provider_symbol: str, start: date, end: date
    ) -> list[DailyClose]:
        response = await self._http.get(
            f"{self.BASE_URL}/{provider_symbol}",
            params={
                "api_token": self._api_key,
                "fmt": "json",
                "from": start.isoformat(),
                "to": end.isoformat(),
            },
        )
        if response.status_code == 404:
            raise SymbolNotSupported(self.name, f"{provider_symbol}: no encontrado")
        if response.status_code == 402:
            raise QuotaExhausted(
                self.name,
                "cuota diaria agotada",
                retry_after=seconds_until_utc_midnight(),
            )
        if response.status_code == 403:
            raise SymbolNotSupported(
                self.name,
                f"{provider_symbol}: fuera del plan ({self._http.snippet(response)})",
            )
        if response.status_code != 200:
            raise ProviderUnavailable(
                self.name,
                f"HTTP {response.status_code}: {self._http.snippet(response)}",
            )
        data = self._http.json(response)
        if not isinstance(data, list):
            raise ProviderUnavailable(self.name, "respuesta inesperada")
        closes = [
            DailyClose(
                price_date=date.fromisoformat(row["date"]),
                close=Decimal(str(row["close"])),
            )
            for row in data
            if isinstance(row, dict) and row.get("close") is not None
        ]
        closes.sort(key=lambda c: c.price_date)
        return [c for c in closes if start <= c.price_date <= end]
