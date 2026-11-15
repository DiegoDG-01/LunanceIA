from abc import ABC, abstractmethod

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
