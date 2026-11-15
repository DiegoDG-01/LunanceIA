"""Descarga y guarda los cierres de un valor.

Reglas:
- El valor tiene un proveedor fijo (`preferred_provider`): el primero que respondió. Si
  falla, el siguiente cubre ese día, pero sus precios no pisan los del preferido; cuando el
  preferido vuelve, sobrescribe dentro de la ventana de revisión.
- Si el preferido deja de tener el símbolo, el que respondió pasa a ser el preferido.
- Los proveedores que responden que no tienen el símbolo quedan `UNSUPPORTED` y el router
  ya no les pregunta por ese valor.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import cast

from application.interfaces.market_data import MarketDataGateway, ProviderName
from domain.entities.securities.instrument import Instrument
from domain.entities.securities.instrument_price import InstrumentPrice
from domain.entities.securities.instrument_provider_symbol import (
    InstrumentProviderSymbol,
)
from domain.objects.enums import ProviderSymbolStatus
from domain.repositories.securities.instrument_repository import (
    InstrumentProviderSymbolRepository,
    InstrumentRepository,
)
from domain.repositories.securities.price_repository import InstrumentPriceRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class InstrumentSyncResult:
    instrument_id: int
    provider: str
    received: int
    saved: int


def _provider(value: str | None) -> ProviderName | None:
    try:
        return ProviderName(value) if value else None
    except ValueError:
        return None


class InstrumentPriceSync:
    def __init__(
        self,
        *,
        instrument_repository: InstrumentRepository,
        symbol_repository: InstrumentProviderSymbolRepository,
        price_repository: InstrumentPriceRepository,
        gateway: MarketDataGateway,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._instruments = instrument_repository
        self._symbols = symbol_repository
        self._prices = price_repository
        self._gateway = gateway
        self._clock = clock

    async def sync(
        self, instrument: Instrument, start: date, end: date
    ) -> InstrumentSyncResult:
        """Lanza `NoProviderAvailable` si ningún proveedor respondió. No hace commit."""
        instrument_id = cast(int, instrument.id)
        known = await self._symbols.get_for_instrument(instrument_id)
        provider_symbols = {
            name: s.provider_symbol
            for s in known
            if s.status is ProviderSymbolStatus.ACTIVE
            and (name := _provider(s.provider)) is not None
        }
        skip = frozenset(
            name
            for s in known
            if s.status is ProviderSymbolStatus.UNSUPPORTED
            and (name := _provider(s.provider)) is not None
        )
        preferred = _provider(instrument.preferred_provider)

        routed = await self._gateway.fetch_daily_closes(
            instrument.market,
            instrument.symbol,
            start,
            end,
            preferred=preferred,
            provider_symbols=provider_symbols,
            skip=skip,
        )
        now = self._clock()

        for attempt in routed.attempts:
            if attempt.outcome == "unsupported" and attempt.provider not in skip:
                await self._symbols.save(
                    InstrumentProviderSymbol(
                        instrument_id=instrument_id,
                        provider=attempt.provider.value,
                        provider_symbol=attempt.provider_symbol,
                        status=ProviderSymbolStatus.UNSUPPORTED,
                        checked_at=now,
                    )
                )
        if provider_symbols.get(routed.provider) != routed.provider_symbol:
            await self._symbols.save(
                InstrumentProviderSymbol(
                    instrument_id=instrument_id,
                    provider=routed.provider.value,
                    provider_symbol=routed.provider_symbol,
                    status=ProviderSymbolStatus.ACTIVE,
                    checked_at=now,
                )
            )

        preferred_gone = preferred is not None and (
            preferred in skip or preferred in routed.unsupported
        )
        if preferred is None or preferred_gone:
            if preferred_gone:
                logger.info(
                    "Preferred market data provider dropped the symbol; switching",
                    extra={
                        "instrument_id": instrument_id,
                        "from": preferred.value if preferred else None,
                        "to": routed.provider.value,
                    },
                )
            instrument.preferred_provider = routed.provider.value
            await self._instruments.save(instrument)
            preferred = routed.provider

        from_fallback = routed.provider is not preferred
        existing = {
            p.price_date: p
            for p in await self._prices.get_range(instrument_id, start, end)
        }
        to_save = []
        for close in routed.closes:
            current = existing.get(close.price_date)
            if (
                from_fallback
                and current is not None
                and current.provider == cast(ProviderName, preferred).value
            ):
                continue
            if (
                current is not None
                and current.provider == routed.provider.value
                and current.close == close.close
                and current.traded_value == close.traded_value
                and current.is_trading_day == close.is_trading_day
            ):
                continue
            to_save.append(
                InstrumentPrice(
                    instrument_id=instrument_id,
                    price_date=close.price_date,
                    close=close.close,
                    provider=routed.provider.value,
                    traded_value=close.traded_value,
                    is_trading_day=close.is_trading_day,
                    fetched_at=now,
                )
            )
        if to_save:
            await self._prices.save_many(to_save)
        return InstrumentSyncResult(
            instrument_id=instrument_id,
            provider=routed.provider.value,
            received=len(routed.closes),
            saved=len(to_save),
        )
