"""DataBursatil (https://databursatil.com/docs.html): BMV, BIVA y SIC en pesos.

`/v2/historicos` responde `{"2026-11-13": [precio, importe], ...}`. Los feriados de la BMV
vienen rellenos con el cierre anterior e importe 0: se marcan como día sin operación. Los
errores llegan como 400 con `{"Error": ...}`; el texto distingue símbolo desconocido de rango
sin resultados.
"""

from datetime import date
from decimal import Decimal

import httpx

from application.interfaces.market_data import (
    DailyClose,
    InstrumentCatalogSource,
    InstrumentListing,
    MarketDataProvider,
    ProviderName,
    ProviderUnavailable,
    SymbolNotSupported,
)
from domain.objects.enums import InstrumentType, Market
from infrastructure.external_services.market_data.provider_http import ProviderHttp

# `/v2/emisoras?mercado=`: local es BMV y BIVA; global es el SIC.
_CATALOG_SEGMENT = {Market.BMV: "local", Market.SIC: "global"}


class DataBursatilProvider(MarketDataProvider, InstrumentCatalogSource):
    name = ProviderName.DATABURSATIL
    markets = frozenset({Market.BMV, Market.SIC})
    catalog_markets = frozenset(_CATALOG_SEGMENT)
    BASE_URL = "https://api.databursatil.com/v2"

    def __init__(
        self, *, token: str, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        if not token:
            raise ValueError("DataBursatilProvider necesita DATABURSATIL_TOKEN")
        self._token = token
        self._http = ProviderHttp(self.name, secret=token, transport=transport)

    def provider_symbol(self, market: Market, symbol: str) -> str:
        # El catálogo ya usa emisora + serie al estilo de la BMV (`WALMEX*`, `FUNO11`).
        return symbol

    async def fetch_daily_closes(
        self, provider_symbol: str, start: date, end: date
    ) -> list[DailyClose]:
        response = await self._http.get(
            f"{self.BASE_URL}/historicos",
            params={
                "token": self._token,
                "inicio": start.isoformat(),
                "final": end.isoformat(),
                "emisora_serie": provider_symbol,
            },
        )
        data = self._http.json(response)
        if response.status_code != 200:
            message = str(data.get("Error", "")) if isinstance(data, dict) else ""
            lowered = message.lower()
            if "no arrojo ningun resultado" in lowered:
                return []
            if "desconocida" in lowered:
                raise SymbolNotSupported(
                    self.name, f"{provider_symbol}: {message[:120]}"
                )
            raise ProviderUnavailable(
                self.name,
                f"HTTP {response.status_code}: {self._http.snippet(response)}",
            )
        if not isinstance(data, dict):
            raise ProviderUnavailable(self.name, "respuesta inesperada")
        closes = []
        for day, values in data.items():
            price, traded = _price_and_amount(values)
            if price is None:
                continue
            closes.append(
                DailyClose(
                    price_date=date.fromisoformat(day),
                    close=price,
                    traded_value=traded,
                    is_trading_day=traded is None or traded != 0,
                )
            )
        closes.sort(key=lambda c: c.price_date)
        return [c for c in closes if start <= c.price_date <= end]

    async def fetch_catalog(self, market: Market) -> list[InstrumentListing]:
        """Todas las emisoras del mercado, activas y suspendidas. Responde
        `{"WALMEX": {"*": {"razon_social": ..., "isin": ..., "estatus": "ACTIVA", ...}}}`.
        Cuesta ~470 créditos (local) y ~1,800 (global)."""
        segment = _CATALOG_SEGMENT.get(market)
        if segment is None:
            raise SymbolNotSupported(self.name, f"sin catálogo para {market.value}")
        response = await self._http.get(
            f"{self.BASE_URL}/emisoras",
            params={"token": self._token, "mercado": segment},
        )
        data = self._http.json(response)
        if response.status_code != 200 or not isinstance(data, dict):
            raise ProviderUnavailable(
                self.name,
                f"HTTP {response.status_code}: {self._http.snippet(response)}",
            )
        listings: dict[str, InstrumentListing] = {}
        for issuer, series in data.items():
            if not isinstance(series, dict) or issuer in ("", "None"):
                continue
            for serie, info in series.items():
                if not isinstance(info, dict) or serie in ("", "None"):
                    continue
                symbol = f"{issuer}{serie}".strip().upper()
                if not symbol or len(symbol) > 30:
                    continue
                isin = str(info.get("isin") or "").strip().upper()
                listings[symbol] = InstrumentListing(
                    market=market,
                    symbol=symbol,
                    name=str(info.get("razon_social") or symbol).strip()[:255],
                    instrument_type=_instrument_type(
                        str(info.get("tipo_valor_descripcion") or "")
                    ),
                    currency="MXN",
                    isin=isin if len(isin) == 12 else None,
                    exchange=(str(info.get("bolsa") or "").strip()[:60] or None),
                    is_active=str(info.get("estatus") or "").upper() == "ACTIVA",
                )
        return list(listings.values())

    async def remaining_credits(self) -> int | None:
        """Créditos del mes que quedan (1 crédito por KiB de respuesta)."""
        response = await self._http.get(
            f"{self.BASE_URL}/creditos", params={"token": self._token}
        )
        data = self._http.json(response)
        if response.status_code != 200 or not isinstance(data, dict):
            return None
        value = data.get("disponibles")
        return int(value) if isinstance(value, int | float) else None


def _price_and_amount(values) -> tuple[Decimal | None, Decimal | None]:
    if isinstance(values, list):
        price = values[0] if values else None
        amount = values[1] if len(values) > 1 else None
    elif isinstance(values, dict):
        price, amount = values.get("precio"), values.get("importe")
    else:
        price, amount = values, None
    return _decimal(price), _decimal(amount)


def _decimal(value) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except ArithmeticError:
        return None


def _instrument_type(description: str) -> InstrumentType:
    """Por la descripción del tipo de valor de la BMV: los códigos varían entre segmentos."""
    text = description.upper()
    if "FIBRA" in text:
        return InstrumentType.FIBRA
    if "TRAC" in text or "CANASTA" in text:
        return InstrumentType.ETF
    if text.startswith("ACCIONES"):
        return InstrumentType.STOCK
    return InstrumentType.OTHER
