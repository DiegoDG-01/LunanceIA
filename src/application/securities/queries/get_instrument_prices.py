from dataclasses import dataclass
from datetime import date
from typing import cast

from domain.entities.securities.instrument import Instrument
from domain.entities.securities.instrument_price import InstrumentPrice
from domain.repositories.securities.instrument_repository import InstrumentRepository
from domain.repositories.securities.price_repository import InstrumentPriceRepository
from shared.exceptions.domain import InstrumentNotFoundError


@dataclass
class GetInstrumentPricesQuery:
    instrument_uuid: str
    start: date
    end: date


@dataclass(frozen=True, slots=True)
class InstrumentPrices:
    instrument: Instrument
    prices: list[InstrumentPrice]


class GetInstrumentPricesHandler:
    def __init__(
        self,
        *,
        instrument_repository: InstrumentRepository,
        price_repository: InstrumentPriceRepository,
    ) -> None:
        self._instruments = instrument_repository
        self._prices = price_repository

    async def handle(self, query: GetInstrumentPricesQuery) -> InstrumentPrices:
        instrument = await self._instruments.get_by_uuid(query.instrument_uuid)
        if instrument is None:
            raise InstrumentNotFoundError(query.instrument_uuid)
        prices = await self._prices.get_range(
            cast(int, instrument.id), query.start, query.end
        )
        return InstrumentPrices(instrument=instrument, prices=prices)
