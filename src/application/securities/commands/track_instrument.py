"""Empieza a seguir los precios de un valor desde una fecha y descarga su historia.

Registrar una operación fija `tracked_since` en su misma transacción y después corre esto en
segundo plano, para no esperar al job de la noche. Si ya hay precios desde el inicio del
seguimiento, no hace nada.
"""

from dataclasses import dataclass
from datetime import date
from typing import cast

from application.interfaces.market_data import NoProviderAvailable
from application.securities.commands.sync_market_data import first_fetch_date
from application.securities.services.price_sync import (
    InstrumentPriceSync,
    InstrumentSyncResult,
)
from domain.repositories.securities.instrument_repository import InstrumentRepository
from domain.repositories.securities.price_repository import InstrumentPriceRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from shared.exceptions.domain import InstrumentNotFoundError


@dataclass
class TrackInstrumentCommand:
    instrument_id: int
    since: date
    as_of: date


@dataclass(frozen=True, slots=True)
class TrackInstrumentResult:
    started: bool
    sync: InstrumentSyncResult | None
    error: str | None = None


class TrackInstrumentHandler:
    def __init__(
        self,
        *,
        instrument_repository: InstrumentRepository,
        price_repository: InstrumentPriceRepository,
        price_sync: InstrumentPriceSync,
        uow: AbstractUnitOfWork,
    ) -> None:
        self._instruments = instrument_repository
        self._prices = price_repository
        self._price_sync = price_sync
        self._uow = uow

    async def handle(self, command: TrackInstrumentCommand) -> TrackInstrumentResult:
        instrument = await self._instruments.get_by_id(command.instrument_id)
        if instrument is None:
            raise InstrumentNotFoundError(str(command.instrument_id))

        started = instrument.track_from(command.since)
        if started:
            instrument = await self._instruments.save(instrument)
            await self._uow.commit()
        tracked_since = cast(date, instrument.tracked_since)
        first = await self._prices.first_price_date(cast(int, instrument.id))
        if first is not None and first <= tracked_since:
            # Ya tiene la historia desde el inicio del seguimiento: el job lo mantiene al día.
            return TrackInstrumentResult(started=started, sync=None)

        start = first_fetch_date(tracked_since)
        end = command.as_of
        if start > end:
            return TrackInstrumentResult(started=started, sync=None)
        try:
            result = await self._price_sync.sync(instrument, start, end)
            await self._uow.commit()
        except NoProviderAvailable as error:
            await self._uow.rollback()
            # El job de la noche lo reintenta: `tracked_since` ya quedó guardado.
            return TrackInstrumentResult(started=started, sync=None, error=str(error))
        return TrackInstrumentResult(started=started, sync=result)
