from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from application.interfaces.market_data import MarketDataGateway
from application.securities.queries.get_instrument_prices import (
    GetInstrumentPricesHandler,
)
from application.securities.queries.search_instruments import SearchInstrumentsHandler
from infrastructure.database.connection import get_db
from infrastructure.database.repositories.sqlalchemy_instrument_repository import (
    SQLAlchemyInstrumentRepository,
)
from infrastructure.database.repositories.sqlalchemy_price_repository import (
    SQLAlchemyInstrumentPriceRepository,
)
from infrastructure.database.repositories.sqlalchemy_unit_of_work import (
    SQLAlchemyUnitOfWork,
)
from infrastructure.external_services.market_data.factory import (
    get_market_data_gateway,
)


def get_market_data() -> MarketDataGateway:
    return get_market_data_gateway()


def get_search_instruments_handler(
    db: AsyncSession = Depends(get_db),
    gateway: MarketDataGateway = Depends(get_market_data),
) -> SearchInstrumentsHandler:
    return SearchInstrumentsHandler(
        instrument_repository=SQLAlchemyInstrumentRepository(db),
        gateway=gateway,
        uow=SQLAlchemyUnitOfWork(db),
    )


def get_instrument_prices_handler(
    db: AsyncSession = Depends(get_db),
) -> GetInstrumentPricesHandler:
    return GetInstrumentPricesHandler(
        instrument_repository=SQLAlchemyInstrumentRepository(db),
        price_repository=SQLAlchemyInstrumentPriceRepository(db),
    )
