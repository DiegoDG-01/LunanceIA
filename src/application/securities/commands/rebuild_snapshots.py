"""Construye o rehace las fotos diarias de las tenencias que lo necesitan.

Por tenencia: desde `snapshots_dirty_from` si algo cambió; si no, desde el día siguiente a
`snapshots_through`; si no tiene fotos, desde su primera operación. Hasta hoy, o hasta el
día en que se cerró. Cada tenencia se confirma por separado y se lee con bloqueo: una
operación simultánea espera y vuelve a marcarla.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import cast

from domain.objects.enums import HoldingStatus
from domain.repositories.securities.instrument_repository import InstrumentRepository
from domain.repositories.securities.price_repository import (
    ExchangeRateRepository,
    InstrumentPriceRepository,
)
from domain.repositories.securities.trade_repository import (
    HoldingSnapshotRepository,
    SecurityHoldingRepository,
    SecurityTradeRepository,
)
from domain.repositories.unit_of_work import AbstractUnitOfWork
from domain.services.holding_snapshots import daily_snapshots

logger = logging.getLogger(__name__)

BASE_CURRENCY = "MXN"


@dataclass
class RebuildSnapshotsCommand:
    as_of: date
    instrument_id: int | None = None


@dataclass
class RebuildSnapshotsStats:
    holdings: int = 0
    rebuilt: int = 0
    failed: int = 0
    snapshots: int = 0
    failures: list[int] = field(default_factory=list)


class RebuildSnapshotsHandler:
    def __init__(
        self,
        *,
        holding_repository: SecurityHoldingRepository,
        trade_repository: SecurityTradeRepository,
        snapshot_repository: HoldingSnapshotRepository,
        instrument_repository: InstrumentRepository,
        price_repository: InstrumentPriceRepository,
        fx_repository: ExchangeRateRepository,
        uow: AbstractUnitOfWork,
    ) -> None:
        self._holdings = holding_repository
        self._trades = trade_repository
        self._snapshots = snapshot_repository
        self._instruments = instrument_repository
        self._prices = price_repository
        self._fx = fx_repository
        self._uow = uow

    async def handle(self, command: RebuildSnapshotsCommand) -> RebuildSnapshotsStats:
        stats = RebuildSnapshotsStats()
        ids = await self._holdings.list_needing_snapshots(
            command.as_of, instrument_id=command.instrument_id
        )
        # Lo leído para elegir no debe dejar abierta la foto de la transacción.
        await self._uow.rollback()
        stats.holdings = len(ids)
        for holding_id in ids:
            try:
                written = await self._rebuild(holding_id, command.as_of)
                await self._uow.commit()
            except Exception:
                await self._uow.rollback()
                stats.failed += 1
                stats.failures.append(holding_id)
                logger.exception(
                    "Failed to rebuild holding snapshots",
                    extra={"holding_id": holding_id},
                )
                continue
            if written is not None:
                stats.rebuilt += 1
                stats.snapshots += written
        return stats

    async def _rebuild(self, holding_id: int, as_of: date) -> int | None:
        holding = await self._holdings.get_by_id(holding_id, for_update=True)
        if holding is None:
            return None
        trades = await self._trades.list_for_holding(
            holding.account_id, holding.instrument_id, for_update=True
        )
        if not trades:
            return None
        instrument = await self._instruments.get_by_id(holding.instrument_id)
        if instrument is None:
            return None

        first_day = min(t.trade_date for t in trades)
        last_day = max(t.trade_date for t in trades)
        # Cerrada: hasta la venta final o un dividendo posterior; abierta: hasta hoy.
        end = (
            max(cast(date, holding.closed_at), last_day)
            if holding.status is HoldingStatus.CLOSED and holding.closed_at
            else as_of
        )
        dirty = holding.snapshots_dirty_from
        if dirty is not None:
            start = dirty
        elif holding.snapshots_through is not None:
            start = holding.snapshots_through + timedelta(days=1)
        else:
            start = first_day
        start = max(start, first_day)

        snapshots = []
        if start <= end:
            before = start - timedelta(days=1)
            prices = await self._prices.get_range(holding.instrument_id, start, end)
            carried = await self._prices.latest_on_or_before(
                [holding.instrument_id], before
            )
            closes = [(p.price_date, p.close) for p in prices]
            if (previous := carried.get(holding.instrument_id)) is not None:
                closes.append((previous.price_date, previous.close))

            fx_rates = None
            if instrument.currency != BASE_CURRENCY:
                rates = await self._fx.get_range(
                    instrument.currency, BASE_CURRENCY, start, end
                )
                fx_rates = [(r.rate_date, r.rate) for r in rates]
                previous_rate = await self._fx.latest_on_or_before(
                    instrument.currency, BASE_CURRENCY, before
                )
                if previous_rate is not None:
                    fx_rates.append((previous_rate.rate_date, previous_rate.rate))

            snapshots = daily_snapshots(
                holding_id=holding_id,
                trades=trades,
                start=start,
                end=end,
                closes=closes,
                fx_rates=fx_rates,
                symbol=instrument.symbol,
            )
        # Borra desde la marca aunque no haya fotos nuevas: una operación movida o borrada
        # puede dejar fotos antes de la nueva primera operación o después del cierre.
        delete_from = min(start, dirty) if dirty is not None else start
        await self._snapshots.replace_from(holding_id, delete_from, snapshots)
        await self._holdings.finish_snapshots(
            holding_id, through=max(end, start - timedelta(days=1)), dirty_from=dirty
        )
        return len(snapshots)
