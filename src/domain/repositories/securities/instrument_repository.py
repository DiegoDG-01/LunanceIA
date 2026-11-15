from abc import ABC, abstractmethod
from collections.abc import Sequence

from domain.entities.securities.instrument import Instrument
from domain.entities.securities.instrument_provider_symbol import (
    InstrumentProviderSymbol,
)
from domain.objects.enums import Market


class InstrumentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, instrument_id: int) -> Instrument | None: ...

    @abstractmethod
    async def get_by_uuid(self, instrument_uuid: str) -> Instrument | None: ...

    @abstractmethod
    async def get_by_market_and_symbols(
        self, market: Market, symbols: Sequence[str]
    ) -> dict[str, Instrument]:
        """Los valores del mercado con esos símbolos, por símbolo."""

    @abstractmethod
    async def search(
        self, query: str, *, market: Market | None = None, limit: int = 20
    ) -> list[Instrument]:
        """Coincidencias por símbolo o nombre: primero el símbolo exacto, luego los que
        empiezan igual, luego por nombre; los activos antes que los suspendidos."""

    @abstractmethod
    async def count_by_market(self, market: Market) -> int: ...

    @abstractmethod
    async def list_tracked(self) -> list[Instrument]:
        """Valores con `tracked_since`: los que el job de precios mantiene al día."""

    @abstractmethod
    async def save(self, instrument: Instrument) -> Instrument:
        """Crea o actualiza (según tenga `id`)."""

    @abstractmethod
    async def save_many(self, instruments: Sequence[Instrument]) -> None:
        """Crea o actualiza varios a la vez (sincronizar el catálogo)."""


class InstrumentProviderSymbolRepository(ABC):
    @abstractmethod
    async def get_for_instrument(
        self, instrument_id: int
    ) -> list[InstrumentProviderSymbol]: ...

    @abstractmethod
    async def save(self, symbol: InstrumentProviderSymbol) -> None:
        """Crea o reemplaza el de (valor, proveedor)."""
