from collections.abc import Sequence
from datetime import date

from sqlalchemy import case, delete, desc, exists, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.securities.holding_snapshot import HoldingSnapshot
from domain.entities.securities.security_holding import SecurityHolding
from domain.entities.securities.security_trade import SecurityTrade
from domain.objects.enums import HoldingStatus
from domain.repositories.securities.trade_repository import (
    HoldingSnapshotRepository,
    SecurityHoldingRepository,
    SecurityTradeRepository,
)
from infrastructure.database.models.instrument import InstrumentModel
from infrastructure.database.models.security_trade import (
    HoldingSnapshotModel,
    SecurityHoldingModel,
    SecurityTradeModel,
)

_TRADE_FIELDS = (
    "user_id",
    "account_id",
    "instrument_id",
    "trade_type",
    "trade_date",
    "quantity",
    "price",
    "fees",
    "tax_withheld",
    "gross_amount",
    "cash_amount",
    "split_from",
    "split_to",
    "transaction_id",
    "notes",
)

_HOLDING_FIELDS = (
    "user_id",
    "account_id",
    "instrument_id",
    "quantity",
    "avg_cost",
    "cost_basis",
    "realized_pnl",
    "dividends",
    "status",
    "opened_at",
    "closed_at",
    "snapshots_through",
    "snapshots_dirty_from",
)


def _trade(model: SecurityTradeModel) -> SecurityTrade:
    return SecurityTrade(
        id=model.id,
        uuid=model.uuid,
        created_at=model.created_at,
        **{f: getattr(model, f) for f in _TRADE_FIELDS},
    )


def _holding(model: SecurityHoldingModel) -> SecurityHolding:
    return SecurityHolding(
        id=model.id,
        uuid=model.uuid,
        updated_at=model.updated_at,
        **{f: getattr(model, f) for f in _HOLDING_FIELDS},
    )


class SQLAlchemySecurityTradeRepository(SecurityTradeRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, trade: SecurityTrade) -> SecurityTrade:
        model = SecurityTradeModel(**{f: getattr(trade, f) for f in _TRADE_FIELDS})
        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)
        return _trade(model)

    async def update(self, trade: SecurityTrade) -> SecurityTrade:
        model = await self.db.get(SecurityTradeModel, trade.id)
        if model is None:
            raise ValueError(f"security trade {trade.id} not found")
        for field in _TRADE_FIELDS:
            setattr(model, field, getattr(trade, field))
        await self.db.flush()
        await self.db.refresh(model)
        return _trade(model)

    async def delete(self, trade_id: int) -> None:
        await self.db.execute(
            delete(SecurityTradeModel).where(SecurityTradeModel.id == trade_id)
        )
        await self.db.flush()

    async def get_by_uuid_and_user_id(
        self, trade_uuid: str, user_id: int, *, for_update: bool = False
    ) -> SecurityTrade | None:
        stmt = select(SecurityTradeModel).where(
            SecurityTradeModel.uuid == trade_uuid,
            SecurityTradeModel.user_id == user_id,
        )
        if for_update:
            stmt = stmt.with_for_update()
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        return _trade(model) if model else None

    async def list_for_holding(
        self, account_id: int, instrument_id: int, *, for_update: bool = False
    ) -> list[SecurityTrade]:
        stmt = (
            select(SecurityTradeModel)
            .where(
                SecurityTradeModel.account_id == account_id,
                SecurityTradeModel.instrument_id == instrument_id,
            )
            .order_by(SecurityTradeModel.trade_date, SecurityTradeModel.id)
        )
        if for_update:
            stmt = stmt.with_for_update()
        result = await self.db.execute(stmt)
        return [_trade(m) for m in result.scalars()]

    async def list_for_user(
        self,
        user_id: int,
        *,
        account_id: int | None = None,
        instrument_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SecurityTrade]:
        stmt = select(SecurityTradeModel).where(SecurityTradeModel.user_id == user_id)
        if account_id is not None:
            stmt = stmt.where(SecurityTradeModel.account_id == account_id)
        if instrument_id is not None:
            stmt = stmt.where(SecurityTradeModel.instrument_id == instrument_id)
        stmt = (
            stmt.order_by(
                desc(SecurityTradeModel.trade_date), desc(SecurityTradeModel.id)
            )
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return [_trade(m) for m in result.scalars()]

    async def exists_for_transaction(self, transaction_id: int) -> bool:
        result = await self.db.execute(
            select(exists().where(SecurityTradeModel.transaction_id == transaction_id))
        )
        return bool(result.scalar())


class SQLAlchemySecurityHoldingRepository(SecurityHoldingRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(
        self, account_id: int, instrument_id: int, *, for_update: bool = False
    ) -> SecurityHolding | None:
        stmt = select(SecurityHoldingModel).where(
            SecurityHoldingModel.account_id == account_id,
            SecurityHoldingModel.instrument_id == instrument_id,
        )
        if for_update:
            stmt = stmt.with_for_update()
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        return _holding(model) if model else None

    async def get_by_uuid_and_user_id(
        self, holding_uuid: str, user_id: int
    ) -> SecurityHolding | None:
        result = await self.db.execute(
            select(SecurityHoldingModel).where(
                SecurityHoldingModel.uuid == holding_uuid,
                SecurityHoldingModel.user_id == user_id,
            )
        )
        model = result.scalar_one_or_none()
        return _holding(model) if model else None

    async def list_for_user(
        self,
        user_id: int,
        *,
        account_id: int | None = None,
        include_closed: bool = False,
    ) -> list[SecurityHolding]:
        stmt = select(SecurityHoldingModel).where(
            SecurityHoldingModel.user_id == user_id
        )
        if account_id is not None:
            stmt = stmt.where(SecurityHoldingModel.account_id == account_id)
        if not include_closed:
            stmt = stmt.where(SecurityHoldingModel.status == HoldingStatus.OPEN)
        stmt = stmt.order_by(SecurityHoldingModel.account_id, SecurityHoldingModel.id)
        result = await self.db.execute(stmt)
        return [_holding(m) for m in result.scalars()]

    async def save(self, holding: SecurityHolding) -> SecurityHolding:
        if holding.id is None:
            model = SecurityHoldingModel(
                **{f: getattr(holding, f) for f in _HOLDING_FIELDS}
            )
            self.db.add(model)
        else:
            # Con bloqueo, no `db.get`: una lectura sin bloqueo usa la foto de la
            # transacción y no vería una tenencia que otra acaba de crear.
            result = await self.db.execute(
                select(SecurityHoldingModel)
                .where(SecurityHoldingModel.id == holding.id)
                .with_for_update()
            )
            model = result.scalar_one_or_none()
            if model is None:
                raise ValueError(f"security holding {holding.id} not found")
            for field in _HOLDING_FIELDS:
                setattr(model, field, getattr(holding, field))
        await self.db.flush()
        await self.db.refresh(model)
        return _holding(model)

    async def delete(self, holding_id: int) -> None:
        await self.db.execute(
            delete(SecurityHoldingModel).where(SecurityHoldingModel.id == holding_id)
        )
        await self.db.flush()

    async def get_by_id(
        self, holding_id: int, *, for_update: bool = False
    ) -> SecurityHolding | None:
        stmt = select(SecurityHoldingModel).where(SecurityHoldingModel.id == holding_id)
        if for_update:
            stmt = stmt.with_for_update()
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        return _holding(model) if model else None

    async def list_needing_snapshots(
        self, as_of: date, *, instrument_id: int | None = None
    ) -> list[int]:
        model = SecurityHoldingModel
        stmt = select(model.id).where(
            or_(
                model.snapshots_dirty_from.is_not(None),
                model.snapshots_through.is_(None),
                (model.status == HoldingStatus.OPEN)
                & (model.snapshots_through < as_of),
            )
        )
        if instrument_id is not None:
            stmt = stmt.where(model.instrument_id == instrument_id)
        result = await self.db.execute(stmt.order_by(model.id))
        return list(result.scalars())

    def _mark(self, since: date):
        dirty = SecurityHoldingModel.snapshots_dirty_from
        return case(
            (dirty.is_(None), since),
            (dirty > since, since),
            else_=dirty,
        )

    async def mark_dirty_for_instrument(self, instrument_id: int, since: date) -> None:
        # Solo si ya hay fotos de ese día: las que faltan las agrega la corrida normal.
        await self.db.execute(
            update(SecurityHoldingModel)
            .where(
                SecurityHoldingModel.instrument_id == instrument_id,
                SecurityHoldingModel.snapshots_through >= since,
            )
            .values(snapshots_dirty_from=self._mark(since))
            .execution_options(synchronize_session=False)
        )

    async def mark_dirty_for_currency(self, currency: str, since: date) -> None:
        await self.db.execute(
            update(SecurityHoldingModel)
            .where(
                SecurityHoldingModel.instrument_id.in_(
                    select(InstrumentModel.id).where(
                        InstrumentModel.currency == currency
                    )
                ),
                SecurityHoldingModel.snapshots_through >= since,
            )
            .values(snapshots_dirty_from=self._mark(since))
            .execution_options(synchronize_session=False)
        )

    async def finish_snapshots(
        self, holding_id: int, *, through: date | None, dirty_from: date | None
    ) -> None:
        values: dict = {"snapshots_through": through}
        if dirty_from is not None:
            dirty = SecurityHoldingModel.snapshots_dirty_from
            values["snapshots_dirty_from"] = case(
                (dirty == dirty_from, None), else_=dirty
            )
        await self.db.execute(
            update(SecurityHoldingModel)
            .where(SecurityHoldingModel.id == holding_id)
            .values(**values)
            .execution_options(synchronize_session=False)
        )


_SNAPSHOT_FIELDS = (
    "quantity",
    "close",
    "price_date",
    "fx_rate",
    "market_value",
    "market_value_mxn",
    "cost_basis",
    "realized_pnl",
    "dividends",
    "unrealized_pnl",
)


def _snapshot(model: HoldingSnapshotModel) -> HoldingSnapshot:
    return HoldingSnapshot(
        holding_id=model.holding_id,
        snapshot_date=model.snapshot_date,
        **{f: getattr(model, f) for f in _SNAPSHOT_FIELDS},
    )


class SQLAlchemyHoldingSnapshotRepository(HoldingSnapshotRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def replace_from(
        self, holding_id: int, start: date, snapshots: Sequence[HoldingSnapshot]
    ) -> None:
        await self.db.execute(
            delete(HoldingSnapshotModel).where(
                HoldingSnapshotModel.holding_id == holding_id,
                HoldingSnapshotModel.snapshot_date >= start,
            )
        )
        self.db.add_all(
            [
                HoldingSnapshotModel(
                    holding_id=s.holding_id,
                    snapshot_date=s.snapshot_date,
                    **{f: getattr(s, f) for f in _SNAPSHOT_FIELDS},
                )
                for s in snapshots
            ]
        )
        await self.db.flush()
        # Las fotos son muchas y no se vuelven a leer en esta sesión.
        for model in list(self.db.new) + list(self.db.identity_map.values()):
            if isinstance(model, HoldingSnapshotModel):
                self.db.expunge(model)

    async def get_range(
        self, holding_id: int, start: date, end: date
    ) -> list[HoldingSnapshot]:
        result = await self.db.execute(
            select(HoldingSnapshotModel)
            .where(
                HoldingSnapshotModel.holding_id == holding_id,
                HoldingSnapshotModel.snapshot_date >= start,
                HoldingSnapshotModel.snapshot_date <= end,
            )
            .order_by(HoldingSnapshotModel.snapshot_date)
        )
        return [_snapshot(m) for m in result.scalars()]

    async def last_before(self, holding_id: int, day: date) -> HoldingSnapshot | None:
        result = await self.db.execute(
            select(HoldingSnapshotModel)
            .where(
                HoldingSnapshotModel.holding_id == holding_id,
                HoldingSnapshotModel.snapshot_date < day,
            )
            .order_by(HoldingSnapshotModel.snapshot_date.desc())
            .limit(1)
        )
        model = result.scalar_one_or_none()
        return _snapshot(model) if model else None
