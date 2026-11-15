"""Job diario: pone al día los cierres de los valores en seguimiento y el tipo de cambio.

Por cada valor pide desde el último día guardado menos la ventana de revisión (los
proveedores corrigen cierres recientes); si no tiene precios, desde unos días antes de
`tracked_since`, para tener un cierre conocido aunque ese día no haya operado la bolsa. Cada
valor se confirma por separado: uno que falla no deshace a los demás, y la siguiente corrida
lo retoma desde su último día guardado (o desde el principio, si le falta historia).
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import cast

from application.interfaces.market_data import MarketDataGateway, NoProviderAvailable
from application.securities.services.business_days import subtract_business_days
from application.securities.services.price_sync import InstrumentPriceSync
from domain.entities.securities.exchange_rate import ExchangeRate
from domain.entities.securities.instrument import Instrument
from domain.repositories.securities.instrument_repository import InstrumentRepository
from domain.repositories.securities.price_repository import (
    ExchangeRateRepository,
    InstrumentPriceRepository,
)
from domain.repositories.unit_of_work import AbstractUnitOfWork

logger = logging.getLogger(__name__)

# Días hábiles antes de `tracked_since` que se piden la primera vez.
LEAD_BUSINESS_DAYS = 5
FX_PAIRS = (("USD", "MXN"),)


@dataclass
class SyncMarketDataCommand:
    as_of: date
    revision_days: int = 10


@dataclass
class SyncMarketDataStats:
    instruments: int = 0
    synced: int = 0
    skipped: int = 0
    failed: int = 0
    prices_saved: int = 0
    fx_saved: int = 0
    fx_failed: int = 0
    failures: list[str] = field(default_factory=list)


def first_fetch_date(tracked_since: date) -> date:
    return subtract_business_days(tracked_since, LEAD_BUSINESS_DAYS)


def price_window_start(
    tracked_since: date,
    first_saved: date | None,
    last_saved: date | None,
    revision_days: int,
) -> date:
    # Sin precios, o falta la historia del principio (un backfill que falló, o el
    # seguimiento empezó antes): se pide todo desde `tracked_since`.
    if first_saved is None or last_saved is None or first_saved > tracked_since:
        return first_fetch_date(tracked_since)
    return max(
        first_fetch_date(tracked_since),
        subtract_business_days(last_saved, revision_days),
    )


class SyncMarketDataHandler:
    def __init__(
        self,
        *,
        instrument_repository: InstrumentRepository,
        price_repository: InstrumentPriceRepository,
        fx_repository: ExchangeRateRepository,
        price_sync: InstrumentPriceSync,
        gateway: MarketDataGateway,
        uow: AbstractUnitOfWork,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._instruments = instrument_repository
        self._prices = price_repository
        self._fx = fx_repository
        self._price_sync = price_sync
        self._gateway = gateway
        self._uow = uow
        self._clock = clock

    async def handle(self, command: SyncMarketDataCommand) -> SyncMarketDataStats:
        stats = SyncMarketDataStats()
        tracked = await self._instruments.list_tracked()
        stats.instruments = len(tracked)

        for instrument in tracked:
            await self._sync_instrument(instrument, command, stats)

        await self._sync_fx(tracked, command, stats)
        return stats

    async def _sync_instrument(
        self,
        instrument: Instrument,
        command: SyncMarketDataCommand,
        stats: SyncMarketDataStats,
    ) -> None:
        tracked_since = cast(date, instrument.tracked_since)
        instrument_id = cast(int, instrument.id)
        first = await self._prices.first_price_date(instrument_id)
        last = await self._prices.last_price_date(instrument_id)
        start = price_window_start(tracked_since, first, last, command.revision_days)
        if start > command.as_of:
            stats.skipped += 1
            return
        label = f"{instrument.market.value}:{instrument.symbol}"
        try:
            result = await self._price_sync.sync(instrument, start, command.as_of)
            await self._uow.commit()
        except NoProviderAvailable as error:
            await self._uow.rollback()
            stats.failed += 1
            stats.failures.append(str(error))
            logger.warning(
                "No market data provider answered",
                extra={"instrument": label, "detail": str(error)},
            )
            return
        except Exception:
            await self._uow.rollback()
            stats.failed += 1
            stats.failures.append(f"{label}: error inesperado")
            logger.exception(
                "Failed to sync instrument prices", extra={"instrument": label}
            )
            return
        stats.synced += 1
        stats.prices_saved += result.saved

    async def _sync_fx(
        self,
        tracked: list[Instrument],
        command: SyncMarketDataCommand,
        stats: SyncMarketDataStats,
    ) -> None:
        for base, quote in FX_PAIRS:
            needed = [
                cast(date, i.tracked_since) for i in tracked if i.currency == base
            ]
            if not needed:
                continue
            earliest = first_fetch_date(min(needed))
            first = await self._fx.first_rate_date(base, quote)
            last = await self._fx.last_rate_date(base, quote)
            if first is None or last is None or first > earliest:
                start = earliest
            else:
                start = max(
                    earliest, subtract_business_days(last, command.revision_days)
                )
            if start > command.as_of:
                continue
            try:
                routed = await self._gateway.fetch_fx_rates(
                    base, quote, start, command.as_of
                )
                existing = {
                    r.rate_date: r
                    for r in await self._fx.get_range(base, quote, start, command.as_of)
                }
                now = self._clock()
                to_save = [
                    ExchangeRate(
                        base=base,
                        quote=quote,
                        rate_date=r.rate_date,
                        rate=r.rate,
                        provider=routed.provider.value,
                        fetched_at=now,
                    )
                    for r in routed.rates
                    if (current := existing.get(r.rate_date)) is None
                    or current.rate != r.rate
                    or current.provider != routed.provider.value
                ]
                if to_save:
                    await self._fx.save_many(to_save)
                await self._uow.commit()
                stats.fx_saved += len(to_save)
            except NoProviderAvailable as error:
                await self._uow.rollback()
                stats.fx_failed += 1
                stats.failures.append(str(error))
                logger.warning(
                    "No FX provider answered",
                    extra={"pair": f"{base}/{quote}", "detail": str(error)},
                )
            except Exception:
                await self._uow.rollback()
                stats.fx_failed += 1
                stats.failures.append(f"{base}/{quote}: error inesperado")
                logger.exception(
                    "Failed to sync FX rates", extra={"pair": f"{base}/{quote}"}
                )
