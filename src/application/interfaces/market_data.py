"""Puertos de precios de mercado: cierres diarios de acciones, ETFs y FIBRAs, y tipo de cambio.

No es tiempo real: cada proveedor da el cierre de cada día hábil. Los casos de uso piden por
mercado y símbolo y no saben qué proveedor respondió hasta ver el resultado; el router de la
infraestructura elige el proveedor, cuida las cuotas y cambia al siguiente si uno falla.

Símbolos del catálogo (los que reciben los casos de uso):
- BMV y SIC: emisora + serie como las publica la BMV (`WALMEX*`, `FUNO11`, `AAPL*`).
- US: el ticker de la bolsa (`AAPL`, `BRK.B`).
Cada proveedor los traduce a su formato; una traducción guardada (fase 1) tiene prioridad.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum

from domain.objects.enums import Market


class ProviderName(StrEnum):
    DATABURSATIL = "databursatil"
    EODHD = "eodhd"
    TWELVEDATA = "twelvedata"
    YAHOO = "yahoo"
    BANXICO = "banxico"


@dataclass(frozen=True, slots=True)
class DailyClose:
    """Cierre de un día, sin ajustar por splits ni dividendos, en la moneda del valor."""

    price_date: date
    close: Decimal
    # Importe operado en el día (precio × volumen), si el proveedor lo da.
    traded_value: Decimal | None = None
    # False en feriados que el proveedor rellena con el cierre anterior (DataBursatil).
    is_trading_day: bool = True


@dataclass(frozen=True, slots=True)
class FxRate:
    """Unidades de `quote` por una unidad de `base` en `rate_date` (USD/MXN: pesos por dólar)."""

    rate_date: date
    rate: Decimal


class MarketDataError(Exception):
    """Base de los errores de proveedores. `detail` nunca lleva llaves ni tokens."""

    def __init__(self, provider: ProviderName, detail: str) -> None:
        self.provider = provider
        self.detail = detail
        super().__init__(f"{provider.value}: {detail}")


class ProviderUnavailable(MarketDataError):
    """El proveedor no respondió bien: caído, timeout, 5xx o llave inválida."""


class SymbolNotSupported(MarketDataError):
    """El proveedor no conoce el símbolo o su plan no lo cubre. No vale la pena reintentarlo."""


class QuotaExhausted(MarketDataError):
    """Se acabó la cuota del proveedor; vuelve a haber en `retry_after` segundos."""

    def __init__(
        self, provider: ProviderName, detail: str, *, retry_after: int
    ) -> None:
        super().__init__(provider, detail)
        self.retry_after = retry_after


@dataclass(frozen=True, slots=True)
class ProviderAttempt:
    provider: ProviderName
    # `unavailable`, `unsupported`, `quota`, `down` (marcado caído) o `not_configured`.
    outcome: str
    detail: str = ""


class NoProviderAvailable(Exception):
    """Ningún proveedor de la ruta pudo responder. `attempts` dice qué pasó con cada uno."""

    def __init__(self, what: str, attempts: Sequence[ProviderAttempt]) -> None:
        self.attempts = tuple(attempts)
        summary = ", ".join(f"{a.provider.value}={a.outcome}" for a in self.attempts)
        super().__init__(f"{what}: {summary or 'sin proveedores en la ruta'}")


class MarketDataProvider(ABC):
    """Un proveedor de cierres diarios."""

    name: ProviderName
    markets: frozenset[Market]

    @abstractmethod
    def provider_symbol(self, market: Market, symbol: str) -> str:
        """Traducción por defecto del símbolo del catálogo al formato del proveedor."""

    @abstractmethod
    async def fetch_daily_closes(
        self, provider_symbol: str, start: date, end: date
    ) -> list[DailyClose]:
        """Cierres de `start` a `end` (ambos incluidos), ordenados por fecha. Lista vacía si
        no hubo días hábiles en el rango. Lanza `ProviderUnavailable`, `SymbolNotSupported`
        o `QuotaExhausted`."""


class FxRateProvider(ABC):
    name: ProviderName

    @abstractmethod
    def supports(self, base: str, quote: str) -> bool: ...

    @abstractmethod
    async def fetch_rates(
        self, base: str, quote: str, start: date, end: date
    ) -> list[FxRate]:
        """Tipos de cambio de `start` a `end` (incluidos), ordenados por fecha."""


@dataclass(frozen=True, slots=True)
class RoutedCloses:
    """Lo que devolvió el router: los cierres y qué proveedor los dio."""

    provider: ProviderName
    provider_symbol: str
    closes: list[DailyClose]
    # Proveedores que respondieron que no tienen el símbolo: se guardan como `UNSUPPORTED`.
    unsupported: tuple[ProviderName, ...] = ()
    attempts: tuple[ProviderAttempt, ...] = field(default=())


@dataclass(frozen=True, slots=True)
class RoutedRates:
    provider: ProviderName
    rates: list[FxRate]


class MarketDataGateway(ABC):
    """Lo que usan los casos de uso: pedir por mercado y dejar que el router elija."""

    @abstractmethod
    def providers_for(self, market: Market) -> tuple[ProviderName, ...]:
        """Proveedores configurados para el mercado, en orden de preferencia."""

    @abstractmethod
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
        """Pregunta primero a `preferred` (si está en la ruta) y luego al resto, en orden.
        `provider_symbols` reemplaza la traducción por defecto; `skip` son los proveedores ya
        marcados como `UNSUPPORTED` para ese valor. Lanza `NoProviderAvailable`."""

    @abstractmethod
    async def fetch_fx_rates(
        self, base: str, quote: str, start: date, end: date
    ) -> RoutedRates:
        """Lanza `NoProviderAvailable` si ningún proveedor de tipo de cambio respondió."""
