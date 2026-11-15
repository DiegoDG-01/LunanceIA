from collections.abc import Sequence
from datetime import UTC, date, datetime

from sqlalchemy import func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.securities.exchange_rate import ExchangeRate
from domain.entities.securities.instrument_price import InstrumentPrice
from domain.repositories.securities.price_repository import (
    ExchangeRateRepository,
    InstrumentPriceRepository,
)
from infrastructure.database.models.instrument import (
    ExchangeRateModel,
    InstrumentPriceModel,
)

# Cuántas llaves por `IN` al buscar las filas que ya existen.
_BATCH = 500


class SQLAlchemyInstrumentPriceRepository(InstrumentPriceRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def first_price_date(self, instrument_id: int) -> date | None:
        result = await self.db.execute(
            select(func.min(InstrumentPriceModel.price_date)).where(
                InstrumentPriceModel.instrument_id == instrument_id
            )
        )
        return result.scalar_one_or_none()

    async def last_price_date(self, instrument_id: int) -> date | None:
        result = await self.db.execute(
            select(func.max(InstrumentPriceModel.price_date)).where(
                InstrumentPriceModel.instrument_id == instrument_id
            )
        )
        return result.scalar_one_or_none()

    async def get_range(
        self, instrument_id: int, start: date, end: date
    ) -> list[InstrumentPrice]:
        result = await self.db.execute(
            select(InstrumentPriceModel)
            .where(
                InstrumentPriceModel.instrument_id == instrument_id,
                InstrumentPriceModel.price_date >= start,
                InstrumentPriceModel.price_date <= end,
            )
            .order_by(InstrumentPriceModel.price_date)
        )
        return [
            InstrumentPrice(
                instrument_id=m.instrument_id,
                price_date=m.price_date,
                close=m.close,
                provider=m.provider,
                traded_value=m.traded_value,
                is_trading_day=m.is_trading_day,
                fetched_at=m.fetched_at,
            )
            for m in result.scalars()
        ]

    async def save_many(self, prices: Sequence[InstrumentPrice]) -> None:
        # Portable (MySQL y SQLite de los tests): se leen las que existen y se actualizan.
        keys = [(p.instrument_id, p.price_date) for p in prices]
        existing: dict[tuple[int, date], InstrumentPriceModel] = {}
        for i in range(0, len(keys), _BATCH):
            result = await self.db.execute(
                select(InstrumentPriceModel).where(
                    tuple_(
                        InstrumentPriceModel.instrument_id,
                        InstrumentPriceModel.price_date,
                    ).in_(keys[i : i + _BATCH])
                )
            )
            existing.update(
                {(m.instrument_id, m.price_date): m for m in result.scalars()}
            )
        for price in prices:
            model = existing.get((price.instrument_id, price.price_date))
            if model is None:
                model = InstrumentPriceModel(
                    instrument_id=price.instrument_id, price_date=price.price_date
                )
                self.db.add(model)
                existing[(price.instrument_id, price.price_date)] = model
            model.close = price.close
            model.traded_value = price.traded_value
            model.is_trading_day = price.is_trading_day
            model.provider = price.provider
            model.fetched_at = price.fetched_at or datetime.now(UTC)
        await self.db.flush()


class SQLAlchemyExchangeRateRepository(ExchangeRateRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def first_rate_date(self, base: str, quote: str) -> date | None:
        result = await self.db.execute(
            select(func.min(ExchangeRateModel.rate_date)).where(
                ExchangeRateModel.base == base, ExchangeRateModel.quote == quote
            )
        )
        return result.scalar_one_or_none()

    async def last_rate_date(self, base: str, quote: str) -> date | None:
        result = await self.db.execute(
            select(func.max(ExchangeRateModel.rate_date)).where(
                ExchangeRateModel.base == base, ExchangeRateModel.quote == quote
            )
        )
        return result.scalar_one_or_none()

    async def get_range(
        self, base: str, quote: str, start: date, end: date
    ) -> list[ExchangeRate]:
        result = await self.db.execute(
            select(ExchangeRateModel)
            .where(
                ExchangeRateModel.base == base,
                ExchangeRateModel.quote == quote,
                ExchangeRateModel.rate_date >= start,
                ExchangeRateModel.rate_date <= end,
            )
            .order_by(ExchangeRateModel.rate_date)
        )
        return [
            ExchangeRate(
                base=m.base,
                quote=m.quote,
                rate_date=m.rate_date,
                rate=m.rate,
                provider=m.provider,
                fetched_at=m.fetched_at,
            )
            for m in result.scalars()
        ]

    async def save_many(self, rates: Sequence[ExchangeRate]) -> None:
        keys = [(r.base, r.quote, r.rate_date) for r in rates]
        existing: dict[tuple[str, str, date], ExchangeRateModel] = {}
        for i in range(0, len(keys), _BATCH):
            result = await self.db.execute(
                select(ExchangeRateModel).where(
                    tuple_(
                        ExchangeRateModel.base,
                        ExchangeRateModel.quote,
                        ExchangeRateModel.rate_date,
                    ).in_(keys[i : i + _BATCH])
                )
            )
            existing.update(
                {(m.base, m.quote, m.rate_date): m for m in result.scalars()}
            )
        for rate in rates:
            key = (rate.base, rate.quote, rate.rate_date)
            model = existing.get(key)
            if model is None:
                model = ExchangeRateModel(
                    base=rate.base, quote=rate.quote, rate_date=rate.rate_date
                )
                self.db.add(model)
                existing[key] = model
            model.rate = rate.rate
            model.provider = rate.provider
            model.fetched_at = rate.fetched_at or datetime.now(UTC)
        await self.db.flush()
