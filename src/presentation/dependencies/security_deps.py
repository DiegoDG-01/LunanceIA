from collections.abc import Awaitable, Callable
from datetime import date

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from application.interfaces.market_data import MarketDataGateway
from application.securities.commands.delete_trade import DeleteTradeHandler
from application.securities.commands.record_trade import RecordTradeHandler
from application.securities.commands.update_trade import UpdateTradeHandler
from application.securities.queries.get_instrument_prices import (
    GetInstrumentPricesHandler,
)
from application.securities.queries.list_holdings import HoldingQueries
from application.securities.queries.list_trades import ListTradesHandler
from application.securities.queries.search_instruments import SearchInstrumentsHandler
from application.securities.services.trade_bookkeeper import TradeBookkeeper
from application.securities.services.valuation import HoldingValuer
from infrastructure.database.connection import get_db
from infrastructure.database.repositories.sqlalchemy_account_repository import (
    SQLAlchemyAccountRepository,
)
from infrastructure.database.repositories.sqlalchemy_category_repository import (
    SQLAlchemyCategoryRepository,
)
from infrastructure.database.repositories.sqlalchemy_instrument_repository import (
    SQLAlchemyInstrumentRepository,
)
from infrastructure.database.repositories.sqlalchemy_price_repository import (
    SQLAlchemyExchangeRateRepository,
    SQLAlchemyInstrumentPriceRepository,
)
from infrastructure.database.repositories.sqlalchemy_trade_repository import (
    SQLAlchemyHoldingSnapshotRepository,
    SQLAlchemySecurityHoldingRepository,
    SQLAlchemySecurityTradeRepository,
)
from infrastructure.database.repositories.sqlalchemy_transaction_repository import (
    SQLAlchemyTransactionRepository,
)
from infrastructure.database.repositories.sqlalchemy_unit_of_work import (
    SQLAlchemyUnitOfWork,
)
from infrastructure.external_services.market_data.factory import (
    get_market_data_gateway,
)
from infrastructure.scheduler.market_data_jobs import track_instrument_job

InstrumentTracker = Callable[[int, date], Awaitable[None]]


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


def get_instrument_tracker() -> InstrumentTracker:
    """Backfill en segundo plano después de registrar una operación."""
    return track_instrument_job


def _bookkeeper(db: AsyncSession) -> TradeBookkeeper:
    return TradeBookkeeper(
        account_repository=SQLAlchemyAccountRepository(db),
        transaction_repository=SQLAlchemyTransactionRepository(db),
        category_repository=SQLAlchemyCategoryRepository(db),
        instrument_repository=SQLAlchemyInstrumentRepository(db),
        trade_repository=SQLAlchemySecurityTradeRepository(db),
        holding_repository=SQLAlchemySecurityHoldingRepository(db),
    )


def get_record_trade_handler(db: AsyncSession = Depends(get_db)) -> RecordTradeHandler:
    return RecordTradeHandler(bookkeeper=_bookkeeper(db), uow=SQLAlchemyUnitOfWork(db))


def get_update_trade_handler(db: AsyncSession = Depends(get_db)) -> UpdateTradeHandler:
    return UpdateTradeHandler(bookkeeper=_bookkeeper(db), uow=SQLAlchemyUnitOfWork(db))


def get_delete_trade_handler(db: AsyncSession = Depends(get_db)) -> DeleteTradeHandler:
    return DeleteTradeHandler(bookkeeper=_bookkeeper(db), uow=SQLAlchemyUnitOfWork(db))


def get_list_trades_handler(db: AsyncSession = Depends(get_db)) -> ListTradesHandler:
    return ListTradesHandler(
        account_repository=SQLAlchemyAccountRepository(db),
        instrument_repository=SQLAlchemyInstrumentRepository(db),
        trade_repository=SQLAlchemySecurityTradeRepository(db),
    )


def get_holding_queries(db: AsyncSession = Depends(get_db)) -> HoldingQueries:
    return HoldingQueries(
        account_repository=SQLAlchemyAccountRepository(db),
        instrument_repository=SQLAlchemyInstrumentRepository(db),
        holding_repository=SQLAlchemySecurityHoldingRepository(db),
        trade_repository=SQLAlchemySecurityTradeRepository(db),
        valuer=HoldingValuer(
            price_repository=SQLAlchemyInstrumentPriceRepository(db),
            fx_repository=SQLAlchemyExchangeRateRepository(db),
        ),
        snapshot_repository=SQLAlchemyHoldingSnapshotRepository(db),
    )
