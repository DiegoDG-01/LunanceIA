"""Descarga el catálogo de un mercado (BMV/BIVA o SIC) y lo guarda.

Agrega los valores nuevos y actualiza nombre, tipo, ISIN, bolsa y si están activos. No toca
lo que es de la app: el proveedor fijo y desde cuándo se siguen sus precios.
"""

from dataclasses import dataclass

from application.interfaces.market_data import InstrumentListing, MarketDataGateway
from domain.entities.securities.instrument import Instrument
from domain.objects.enums import Market
from domain.repositories.securities.instrument_repository import InstrumentRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork


@dataclass
class SyncInstrumentCatalogCommand:
    market: Market


@dataclass(frozen=True, slots=True)
class CatalogSyncStats:
    market: Market
    received: int
    created: int
    updated: int


def apply_listing(
    instrument: Instrument | None, listing: InstrumentListing
) -> Instrument | None:
    """El valor nuevo o actualizado; None si no cambió nada."""
    if instrument is None:
        return Instrument(
            id=None,
            uuid=None,
            market=listing.market,
            symbol=listing.symbol,
            name=listing.name,
            instrument_type=listing.instrument_type,
            currency=listing.currency,
            isin=listing.isin,
            exchange=listing.exchange,
            is_active=listing.is_active,
        )
    changed = False
    for field, value in (
        ("name", listing.name),
        ("instrument_type", listing.instrument_type),
        ("currency", listing.currency),
        ("isin", listing.isin or instrument.isin),
        ("exchange", listing.exchange or instrument.exchange),
        ("is_active", listing.is_active),
    ):
        if getattr(instrument, field) != value:
            setattr(instrument, field, value)
            changed = True
    return instrument if changed else None


class SyncInstrumentCatalogHandler:
    def __init__(
        self,
        *,
        instrument_repository: InstrumentRepository,
        gateway: MarketDataGateway,
        uow: AbstractUnitOfWork,
    ) -> None:
        self._instruments = instrument_repository
        self._gateway = gateway
        self._uow = uow

    async def handle(self, command: SyncInstrumentCatalogCommand) -> CatalogSyncStats:
        """Lanza `NoProviderAvailable` si nadie dio el catálogo."""
        listings = await self._gateway.fetch_catalog(command.market)
        existing = await self._instruments.get_by_market_and_symbols(
            command.market, [listing.symbol for listing in listings]
        )
        to_save: list[Instrument] = []
        created = 0
        for listing in listings:
            current = existing.get(listing.symbol)
            result = apply_listing(current, listing)
            if result is None:
                continue
            if current is None:
                created += 1
            to_save.append(result)
        if to_save:
            await self._instruments.save_many(to_save)
        await self._uow.commit()
        return CatalogSyncStats(
            market=command.market,
            received=len(listings),
            created=created,
            updated=len(to_save) - created,
        )
