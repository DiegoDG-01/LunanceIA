"""Banxico SIE (https://www.banxico.org.mx/SieAPIRest/): tipo de cambio en pesos.

- USD: el FIX (serie SF43718, pesos por dólar), que se determina una vez por día hábil bancario.
- EUR: la cotización del euro respecto al peso (serie SF46410, de las divisas de la canasta del
  DEG), que Banxico calcula a partir del FIX el mismo día.

Fechas en
`dd/mm/aaaa`; días sin dato llegan como `N/E`. Un rango sin días hábiles devuelve la serie
sin `datos`. Token inválido: 400 con `{"error": {"mensaje": "Token inválido"}}`.
"""

from datetime import date
from decimal import Decimal, InvalidOperation

import httpx

from application.interfaces.market_data import (
    FxRate,
    FxRateProvider,
    ProviderName,
    ProviderUnavailable,
    SymbolNotSupported,
)
from infrastructure.external_services.market_data.provider_http import ProviderHttp

SERIES = {("USD", "MXN"): "SF43718", ("EUR", "MXN"): "SF46410"}


class BanxicoFxProvider(FxRateProvider):
    name = ProviderName.BANXICO
    BASE_URL = "https://www.banxico.org.mx/SieAPIRest/service/v1/series"

    def __init__(
        self, *, token: str, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        if not token:
            raise ValueError("BanxicoFxProvider necesita BANXICO_TOKEN")
        self._token = token
        self._http = ProviderHttp(self.name, secret=token, transport=transport)

    def supports(self, base: str, quote: str) -> bool:
        return (base.upper(), quote.upper()) in SERIES

    async def fetch_rates(
        self, base: str, quote: str, start: date, end: date
    ) -> list[FxRate]:
        series = SERIES.get((base.upper(), quote.upper()))
        if series is None:
            raise SymbolNotSupported(self.name, f"{base}/{quote}: sin serie en Banxico")
        response = await self._http.get(
            f"{self.BASE_URL}/{series}/datos/{start.isoformat()}/{end.isoformat()}",
            headers={"Bmx-Token": self._token, "Accept": "application/json"},
        )
        data = self._http.json(response)
        if response.status_code != 200:
            message = ""
            if isinstance(data, dict) and isinstance(data.get("error"), dict):
                message = str(data["error"].get("mensaje", ""))
            raise ProviderUnavailable(
                self.name,
                f"HTTP {response.status_code}: {message or self._http.snippet(response)}",
            )
        try:
            rows = data["bmx"]["series"][0].get("datos") or []
        except (KeyError, IndexError, TypeError, AttributeError):
            raise ProviderUnavailable(self.name, "respuesta inesperada") from None
        rates = []
        for row in rows:
            value = _rate(row.get("dato"))
            if value is None:
                continue
            day, month, year = row["fecha"].split("/")
            rates.append(
                FxRate(rate_date=date(int(year), int(month), int(day)), rate=value)
            )
        rates.sort(key=lambda r: r.rate_date)
        return [r for r in rates if start <= r.rate_date <= end]


def _rate(value) -> Decimal | None:
    if not isinstance(value, str) or value.strip() in ("", "N/E"):
        return None
    try:
        return Decimal(value.replace(",", ""))
    except InvalidOperation:
        return None
