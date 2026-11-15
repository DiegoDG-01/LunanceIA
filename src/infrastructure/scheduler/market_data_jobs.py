"""Jobs de precios de mercado: cierres diarios, tipo de cambio y catálogo de valores."""

import logging
from datetime import UTC, datetime

from application.interfaces.market_data import NoProviderAvailable
from application.securities.commands.sync_instrument_catalog import (
    SyncInstrumentCatalogCommand,
    SyncInstrumentCatalogHandler,
)
from application.securities.commands.sync_market_data import (
    SyncMarketDataCommand,
    SyncMarketDataHandler,
)
from application.securities.services.price_sync import InstrumentPriceSync
from domain.objects.enums import Market
from infrastructure.config.settings import settings
from infrastructure.database.connection import AsyncSessionLocal
from infrastructure.database.repositories.sqlalchemy_instrument_repository import (
    SQLAlchemyInstrumentProviderSymbolRepository,
    SQLAlchemyInstrumentRepository,
)
from infrastructure.database.repositories.sqlalchemy_price_repository import (
    SQLAlchemyExchangeRateRepository,
    SQLAlchemyInstrumentPriceRepository,
)
from infrastructure.database.repositories.sqlalchemy_unit_of_work import (
    SQLAlchemyUnitOfWork,
)
from infrastructure.external_services.market_data.factory import (
    get_market_data_gateway,
)

logger = logging.getLogger(__name__)


async def sync_market_data_job() -> None:
    """Pone al día cierres y tipo de cambio. Corre a la 01:00 UTC (las bolsas ya cerraron)
    y se repite a las 13:00 UTC para recoger lo que haya fallado o se haya corregido."""
    gateway = get_market_data_gateway()
    async with AsyncSessionLocal() as db:
        try:
            instruments = SQLAlchemyInstrumentRepository(db)
            prices = SQLAlchemyInstrumentPriceRepository(db)
            handler = SyncMarketDataHandler(
                instrument_repository=instruments,
                price_repository=prices,
                fx_repository=SQLAlchemyExchangeRateRepository(db),
                price_sync=InstrumentPriceSync(
                    instrument_repository=instruments,
                    symbol_repository=SQLAlchemyInstrumentProviderSymbolRepository(db),
                    price_repository=prices,
                    gateway=gateway,
                ),
                gateway=gateway,
                uow=SQLAlchemyUnitOfWork(db),
            )
            stats = await handler.handle(
                SyncMarketDataCommand(
                    as_of=datetime.now(UTC).date(),
                    revision_days=settings.MARKET_DATA_REVISION_DAYS,
                )
            )
            logger.info(
                "Market data sync finished",
                extra={
                    "instruments": stats.instruments,
                    "synced": stats.synced,
                    "failed": stats.failed,
                    "prices_saved": stats.prices_saved,
                    "fx_saved": stats.fx_saved,
                    "fx_failed": stats.fx_failed,
                },
            )
        except Exception:
            await db.rollback()
            logger.exception("Error running market data sync job")


async def sync_instrument_catalog_job() -> None:
    """Actualiza el catálogo de BMV/BIVA y SIC (valores nuevos, suspendidos, nombres)."""
    gateway = get_market_data_gateway()
    for market in Market:
        if not gateway.has_catalog(market):
            continue
        async with AsyncSessionLocal() as db:
            try:
                handler = SyncInstrumentCatalogHandler(
                    instrument_repository=SQLAlchemyInstrumentRepository(db),
                    gateway=gateway,
                    uow=SQLAlchemyUnitOfWork(db),
                )
                stats = await handler.handle(
                    SyncInstrumentCatalogCommand(market=market)
                )
                logger.info(
                    "Instrument catalog synced",
                    extra={
                        "market": market.value,
                        "received": stats.received,
                        "instruments_created": stats.created,
                        "instruments_updated": stats.updated,
                    },
                )
            except NoProviderAvailable as error:
                await db.rollback()
                logger.warning(
                    "Instrument catalog unavailable",
                    extra={"market": market.value, "detail": str(error)},
                )
            except Exception:
                await db.rollback()
                logger.exception(
                    "Error syncing instrument catalog", extra={"market": market.value}
                )
