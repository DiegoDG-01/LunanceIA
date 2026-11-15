from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import date

from domain.entities.securities.holding_snapshot import HoldingSnapshot
from domain.entities.securities.security_holding import SecurityHolding
from domain.entities.securities.security_trade import SecurityTrade


class SecurityTradeRepository(ABC):
    @abstractmethod
    async def create(self, trade: SecurityTrade) -> SecurityTrade: ...

    @abstractmethod
    async def update(self, trade: SecurityTrade) -> SecurityTrade: ...

    @abstractmethod
    async def delete(self, trade_id: int) -> None: ...

    @abstractmethod
    async def get_by_uuid_and_user_id(
        self, trade_uuid: str, user_id: int, *, for_update: bool = False
    ) -> SecurityTrade | None: ...

    @abstractmethod
    async def list_for_holding(
        self, account_id: int, instrument_id: int, *, for_update: bool = False
    ) -> list[SecurityTrade]:
        """Todas las operaciones del valor en la cuenta, en orden. `for_update` las lee con
        bloqueo: ve lo último confirmado aunque la transacción ya tenga una foto vieja."""

    @abstractmethod
    async def list_for_user(
        self,
        user_id: int,
        *,
        account_id: int | None = None,
        instrument_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SecurityTrade]:
        """Las más recientes primero."""

    @abstractmethod
    async def exists_for_transaction(self, transaction_id: int) -> bool:
        """True si la transacción es el movimiento de dinero de una operación."""


class SecurityHoldingRepository(ABC):
    @abstractmethod
    async def get(
        self, account_id: int, instrument_id: int, *, for_update: bool = False
    ) -> SecurityHolding | None: ...

    @abstractmethod
    async def get_by_uuid_and_user_id(
        self, holding_uuid: str, user_id: int
    ) -> SecurityHolding | None: ...

    @abstractmethod
    async def list_for_user(
        self,
        user_id: int,
        *,
        account_id: int | None = None,
        include_closed: bool = False,
    ) -> list[SecurityHolding]: ...

    @abstractmethod
    async def save(self, holding: SecurityHolding) -> SecurityHolding:
        """Crea o actualiza (según tenga `id`)."""

    @abstractmethod
    async def delete(self, holding_id: int) -> None: ...

    @abstractmethod
    async def get_by_id(
        self, holding_id: int, *, for_update: bool = False
    ) -> SecurityHolding | None: ...

    @abstractmethod
    async def list_needing_snapshots(
        self, as_of: date, *, instrument_id: int | None = None
    ) -> list[int]:
        """Ids de las tenencias con fotos pendientes: marcadas para rehacer, o abiertas y
        con fotos que no llegan a `as_of`."""

    @abstractmethod
    async def mark_dirty_for_instrument(self, instrument_id: int, since: date) -> None:
        """Pide rehacer las fotos desde `since` de todas las tenencias del valor."""

    @abstractmethod
    async def mark_dirty_for_currency(self, currency: str, since: date) -> None:
        """Lo mismo para las tenencias de valores en `currency` (cambió el tipo de cambio)."""

    @abstractmethod
    async def finish_snapshots(
        self, holding_id: int, *, through: date | None, dirty_from: date | None
    ) -> None:
        """Guarda hasta dónde quedaron las fotos y limpia la marca, pero solo si sigue siendo
        `dirty_from`: si alguien la adelantó mientras tanto, queda para la siguiente vez."""


class HoldingSnapshotRepository(ABC):
    @abstractmethod
    async def replace_from(
        self, holding_id: int, start: date, snapshots: Sequence[HoldingSnapshot]
    ) -> None:
        """Borra las fotos desde `start` y guarda `snapshots`."""

    @abstractmethod
    async def get_range(
        self, holding_id: int, start: date, end: date
    ) -> list[HoldingSnapshot]: ...

    @abstractmethod
    async def last_before(self, holding_id: int, day: date) -> HoldingSnapshot | None:
        """La foto más reciente anterior a `day`."""
