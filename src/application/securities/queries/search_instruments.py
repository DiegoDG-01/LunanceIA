"""Busca valores por símbolo o nombre.

- BMV/BIVA y SIC tienen catálogo completo: se busca en la base. Si el catálogo de un
  mercado todavía no se descargó, se descarga en ese momento (solo la primera vez).
- EE. UU. no tiene catálogo descargable: si la base no tiene el símbolo exacto, se pregunta
  al proveedor y lo que devuelva se agrega al catálogo.

Si un proveedor no responde, se devuelve lo que haya en la base.
"""

import logging
import re
from dataclasses import dataclass

from application.interfaces.market_data import MarketDataGateway, NoProviderAvailable
from application.securities.commands.sync_instrument_catalog import (
    SyncInstrumentCatalogCommand,
    SyncInstrumentCatalogHandler,
    apply_listing,
)
from domain.entities.securities.instrument import Instrument
from domain.objects.enums import Market
from domain.repositories.securities.instrument_repository import InstrumentRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork

logger = logging.getLogger(__name__)

# Lo que parece un ticker: vale la pena preguntar al proveedor si no está en la base.
_TICKER = re.compile(r"^[A-Za-z][A-Za-z0-9.\-]{0,9}$")


@dataclass
class SearchInstrumentsQuery:
    query: str
    market: Market | None = None
    limit: int = 20


class SearchInstrumentsHandler:
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

    async def handle(self, query: SearchInstrumentsQuery) -> list[Instrument]:
        text = query.query.strip()
        if not text:
            return []
        markets = [query.market] if query.market else list(Market)

        for market in markets:
            if self._gateway.has_catalog(
                market
            ) and not await self._instruments.count_by_market(market):
                await self._download_catalog(market)

        results = await self._instruments.search(
            text, market=query.market, limit=query.limit
        )
        if (
            Market.US in markets
            and self._should_ask_provider(text, results)
            and await self._add_from_provider(Market.US, text)
        ):
            results = await self._instruments.search(
                text, market=query.market, limit=query.limit
            )
        return results

    @staticmethod
    def _should_ask_provider(text: str, results: list[Instrument]) -> bool:
        if not results:
            return True
        exact = any(r.market is Market.US and r.symbol == text.upper() for r in results)
        return not exact and bool(_TICKER.match(text))

    async def _download_catalog(self, market: Market) -> None:
        handler = SyncInstrumentCatalogHandler(
            instrument_repository=self._instruments,
            gateway=self._gateway,
            uow=self._uow,
        )
        try:
            await handler.handle(SyncInstrumentCatalogCommand(market=market))
        except NoProviderAvailable as error:
            await self._uow.rollback()
            logger.warning(
                "Instrument catalog unavailable",
                extra={"market": market.value, "detail": str(error)},
            )

    async def _add_from_provider(self, market: Market, text: str) -> bool:
        try:
            listings = await self._gateway.search_instruments(market, text)
        except NoProviderAvailable as error:
            logger.info(
                "Instrument search provider unavailable",
                extra={"market": market.value, "detail": str(error)},
            )
            return False
        if not listings:
            return False
        existing = await self._instruments.get_by_market_and_symbols(
            market, [listing.symbol for listing in listings]
        )
        # Solo se agregan los nuevos: la búsqueda no es la fuente del catálogo.
        new = [
            instrument
            for listing in listings
            if listing.symbol not in existing
            and (instrument := apply_listing(None, listing)) is not None
        ]
        if not new:
            return False
        await self._instruments.save_many(new)
        await self._uow.commit()
        return True
