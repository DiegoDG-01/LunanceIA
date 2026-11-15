from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import date

from domain.entities.securities.exchange_rate import ExchangeRate
from domain.entities.securities.instrument_price import InstrumentPrice


class InstrumentPriceRepository(ABC):
    @abstractmethod
    async def first_price_date(self, instrument_id: int) -> date | None: ...

    @abstractmethod
    async def last_price_date(self, instrument_id: int) -> date | None: ...

    @abstractmethod
    async def get_range(
        self, instrument_id: int, start: date, end: date
    ) -> list[InstrumentPrice]:
        """Precios de `start` a `end` (incluidos), ordenados por fecha."""

    @abstractmethod
    async def save_many(self, prices: Sequence[InstrumentPrice]) -> None:
        """Crea o reemplaza cada (valor, fecha)."""

    @abstractmethod
    async def latest_on_or_before(
        self, instrument_ids: Sequence[int], day: date
    ) -> dict[int, InstrumentPrice]:
        """El último cierre de cada valor hasta `day` (incluido)."""


class ExchangeRateRepository(ABC):
    @abstractmethod
    async def first_rate_date(self, base: str, quote: str) -> date | None: ...

    @abstractmethod
    async def last_rate_date(self, base: str, quote: str) -> date | None: ...

    @abstractmethod
    async def get_range(
        self, base: str, quote: str, start: date, end: date
    ) -> list[ExchangeRate]: ...

    @abstractmethod
    async def save_many(self, rates: Sequence[ExchangeRate]) -> None:
        """Crea o reemplaza cada (base, quote, fecha)."""

    @abstractmethod
    async def latest_on_or_before(
        self, base: str, quote: str, day: date
    ) -> ExchangeRate | None: ...
