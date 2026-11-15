"""Yahoo Finance (API no oficial `v8/finance/chart`): último recurso, apagado por defecto.

Sin llave ni cuota documentada, y puede cambiar sin aviso: solo entra si
`MARKET_DATA_ENABLE_YAHOO` está encendido. Las fechas vienen como timestamps de la apertura;
se pasan a fecha local de la bolsa con `meta.gmtoffset`.
"""

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

import httpx

from application.interfaces.market_data import (
    DailyClose,
    MarketDataProvider,
    ProviderName,
    ProviderUnavailable,
    SymbolNotSupported,
)
from domain.objects.enums import Market
from infrastructure.external_services.market_data.provider_http import ProviderHttp

# Yahoo rechaza clientes sin User-Agent de navegador.
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}


class YahooProvider(MarketDataProvider):
    name = ProviderName.YAHOO
    markets = frozenset({Market.BMV, Market.SIC, Market.US})
    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"

    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._http = ProviderHttp(self.name, transport=transport)

    def provider_symbol(self, market: Market, symbol: str) -> str:
        if market is Market.US:
            return symbol.replace(".", "-")
        return f"{symbol.rstrip('*')}.MX"

    async def fetch_daily_closes(
        self, provider_symbol: str, start: date, end: date
    ) -> list[DailyClose]:
        # Margen de un día a cada lado por las zonas horarias; luego se filtra por fecha local.
        period1 = datetime.combine(start - timedelta(days=1), time(), UTC)
        period2 = datetime.combine(end + timedelta(days=2), time(), UTC)
        response = await self._http.get(
            f"{self.BASE_URL}/{provider_symbol}",
            params={
                "interval": "1d",
                "period1": int(period1.timestamp()),
                "period2": int(period2.timestamp()),
            },
            headers=HEADERS,
        )
        data = self._http.json(response)
        if response.status_code == 404:
            raise SymbolNotSupported(self.name, f"{provider_symbol}: no encontrado")
        if response.status_code != 200:
            raise ProviderUnavailable(
                self.name,
                f"HTTP {response.status_code}: {self._http.snippet(response)}",
            )
        try:
            result = data["chart"]["result"][0]
            offset = int(result["meta"].get("gmtoffset") or 0)
            timestamps = result.get("timestamp") or []
            quotes = result["indicators"]["quote"][0].get("close") or []
        except (KeyError, IndexError, TypeError):
            raise ProviderUnavailable(self.name, "respuesta inesperada") from None
        closes: dict[date, DailyClose] = {}
        for ts, close in zip(timestamps, quotes, strict=False):
            if close is None:
                continue
            day = datetime.fromtimestamp(ts + offset, UTC).date()
            if start <= day <= end:
                # Yahoo da floats; se redondea a 6 decimales, la precisión que se guarda.
                closes[day] = DailyClose(
                    price_date=day, close=round(Decimal(str(close)), 6)
                )
        return [closes[d] for d in sorted(closes)]
