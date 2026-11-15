from collections.abc import Sequence
from datetime import date

from sqlalchemy import case, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.securities.instrument import Instrument
from domain.entities.securities.instrument_provider_symbol import (
    InstrumentProviderSymbol,
)
from domain.objects.enums import Market
from domain.repositories.securities.instrument_repository import (
    InstrumentProviderSymbolRepository,
    InstrumentRepository,
)
from infrastructure.database.models.instrument import (
    InstrumentModel,
    InstrumentProviderSymbolModel,
)

_FIELDS = (
    "market",
    "symbol",
    "name",
    "instrument_type",
    "currency",
    "isin",
    "exchange",
    "preferred_provider",
    "is_active",
    "tracked_since",
)


def _to_entity(model: InstrumentModel) -> Instrument:
    return Instrument(
        id=model.id,
        uuid=model.uuid,
        market=model.market,
        symbol=model.symbol,
        name=model.name,
        instrument_type=model.instrument_type,
        currency=model.currency,
        isin=model.isin,
        exchange=model.exchange,
        preferred_provider=model.preferred_provider,
        is_active=model.is_active,
        tracked_since=model.tracked_since,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class SQLAlchemyInstrumentRepository(InstrumentRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, instrument_id: int) -> Instrument | None:
        model = await self.db.get(InstrumentModel, instrument_id)
        return _to_entity(model) if model else None

    async def get_by_uuid(self, instrument_uuid: str) -> Instrument | None:
        result = await self.db.execute(
            select(InstrumentModel).where(InstrumentModel.uuid == instrument_uuid)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def get_by_market_and_symbols(
        self, market: Market, symbols: Sequence[str]
    ) -> dict[str, Instrument]:
        found: dict[str, Instrument] = {}
        unique = list(dict.fromkeys(symbols))
        # Por lotes: el catálogo del SIC trae miles de símbolos.
        for i in range(0, len(unique), 500):
            result = await self.db.execute(
                select(InstrumentModel).where(
                    InstrumentModel.market == market,
                    InstrumentModel.symbol.in_(unique[i : i + 500]),
                )
            )
            for model in result.scalars():
                found[model.symbol] = _to_entity(model)
        return found

    async def search(
        self, query: str, *, market: Market | None = None, limit: int = 20
    ) -> list[Instrument]:
        text = query.strip()
        if not text:
            return []
        upper = text.upper()
        prefix = f"{_escape_like(upper)}%"
        contains = f"%{_escape_like(text)}%"
        symbol = InstrumentModel.symbol
        rank = case(
            (func.upper(symbol) == upper, 0),
            # `WALMEX` encuentra `WALMEX*` antes que `WALMEXV`.
            (func.upper(symbol) == f"{upper}*", 0),
            (func.upper(symbol).like(prefix, escape="\\"), 1),
            else_=2,
        )
        stmt = select(InstrumentModel).where(
            or_(
                func.upper(symbol).like(prefix, escape="\\"),
                InstrumentModel.name.ilike(contains, escape="\\"),
            )
        )
        if market is not None:
            stmt = stmt.where(InstrumentModel.market == market)
        stmt = stmt.order_by(
            InstrumentModel.is_active.desc(), rank, symbol, InstrumentModel.market
        ).limit(limit)
        result = await self.db.execute(stmt)
        return [_to_entity(m) for m in result.scalars()]

    async def count_by_market(self, market: Market) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(InstrumentModel)
            .where(InstrumentModel.market == market)
        )
        return int(result.scalar_one())

    async def list_tracked(self) -> list[Instrument]:
        result = await self.db.execute(
            select(InstrumentModel)
            .where(InstrumentModel.tracked_since.is_not(None))
            .order_by(InstrumentModel.id)
        )
        return [_to_entity(m) for m in result.scalars()]

    async def get_by_ids(self, instrument_ids: Sequence[int]) -> dict[int, Instrument]:
        unique = list(dict.fromkeys(instrument_ids))
        if not unique:
            return {}
        result = await self.db.execute(
            select(InstrumentModel).where(InstrumentModel.id.in_(unique))
        )
        return {m.id: _to_entity(m) for m in result.scalars()}

    async def track_since(self, instrument_id: int, since: date) -> None:
        await self.db.execute(
            update(InstrumentModel)
            .where(
                InstrumentModel.id == instrument_id,
                or_(
                    InstrumentModel.tracked_since.is_(None),
                    InstrumentModel.tracked_since > since,
                ),
            )
            .values(tracked_since=since)
            .execution_options(synchronize_session=False)
        )
        await self.db.flush()

    async def save(self, instrument: Instrument) -> Instrument:
        if instrument.id is None:
            model = InstrumentModel(**{f: getattr(instrument, f) for f in _FIELDS})
            self.db.add(model)
        else:
            model = await self.db.get(InstrumentModel, instrument.id)
            if model is None:
                raise ValueError(f"instrument {instrument.id} not found")
            for field in _FIELDS:
                setattr(model, field, getattr(instrument, field))
        await self.db.flush()
        await self.db.refresh(model)
        return _to_entity(model)

    async def save_many(self, instruments: Sequence[Instrument]) -> None:
        existing_ids = [i.id for i in instruments if i.id is not None]
        models: dict[int, InstrumentModel] = {}
        for i in range(0, len(existing_ids), 500):
            result = await self.db.execute(
                select(InstrumentModel).where(
                    InstrumentModel.id.in_(existing_ids[i : i + 500])
                )
            )
            models.update({m.id: m for m in result.scalars()})
        for instrument in instruments:
            model = models.get(instrument.id) if instrument.id is not None else None
            if model is None:
                self.db.add(
                    InstrumentModel(**{f: getattr(instrument, f) for f in _FIELDS})
                )
            else:
                for field in _FIELDS:
                    setattr(model, field, getattr(instrument, field))
        await self.db.flush()


class SQLAlchemyInstrumentProviderSymbolRepository(InstrumentProviderSymbolRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_for_instrument(
        self, instrument_id: int
    ) -> list[InstrumentProviderSymbol]:
        result = await self.db.execute(
            select(InstrumentProviderSymbolModel).where(
                InstrumentProviderSymbolModel.instrument_id == instrument_id
            )
        )
        return [
            InstrumentProviderSymbol(
                instrument_id=m.instrument_id,
                provider=m.provider,
                provider_symbol=m.provider_symbol,
                status=m.status,
                checked_at=m.checked_at,
            )
            for m in result.scalars()
        ]

    async def save(self, symbol: InstrumentProviderSymbol) -> None:
        model = await self.db.get(
            InstrumentProviderSymbolModel, (symbol.instrument_id, symbol.provider)
        )
        if model is None:
            model = InstrumentProviderSymbolModel(
                instrument_id=symbol.instrument_id, provider=symbol.provider
            )
            self.db.add(model)
        model.provider_symbol = symbol.provider_symbol
        model.status = symbol.status
        if symbol.checked_at is not None:
            model.checked_at = symbol.checked_at
        await self.db.flush()
