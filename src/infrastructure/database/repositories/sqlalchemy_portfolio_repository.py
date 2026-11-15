from datetime import date
from decimal import Decimal

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from application.securities.portfolio_repository import (
    AccountBalance,
    HoldingCoverage,
    PortfolioReadRepository,
    PositionBalance,
    PositionSeries,
    SnapshotDayTotal,
)
from domain.objects.enums import HoldingStatus, PositionStatus
from infrastructure.database.models import (
    AccountModel,
    HoldingSnapshotModel,
    InvestmentPositionModel,
    InvestmentYieldModel,
    SecurityHoldingModel,
)


def _decimal(value) -> Decimal:
    # SQLite devuelve float en SUM sobre DECIMAL; MySQL, Decimal.
    return value if isinstance(value, Decimal) else Decimal(str(value or 0))


class SQLAlchemyPortfolioReadRepository(PortfolioReadRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    def _user_positions(self, user_id: int):
        return (
            select(InvestmentPositionModel.id)
            .join(AccountModel, AccountModel.id == InvestmentPositionModel.account_id)
            .where(AccountModel.user_id == user_id)
        )

    async def account_balances(self, user_id: int) -> list[AccountBalance]:
        result = await self.db.execute(
            select(
                AccountModel.type, AccountModel.currency, AccountModel.current_balance
            ).where(AccountModel.user_id == user_id)
        )
        return [
            AccountBalance(account_type=t, currency=c, balance=_decimal(b))
            for t, c, b in result.all()
        ]

    async def position_balances(self, user_id: int) -> list[PositionBalance]:
        result = await self.db.execute(
            select(
                InvestmentPositionModel.currency,
                InvestmentPositionModel.balance,
                InvestmentPositionModel.accrued_yield,
            )
            .join(AccountModel, AccountModel.id == InvestmentPositionModel.account_id)
            .where(
                AccountModel.user_id == user_id,
                InvestmentPositionModel.status != PositionStatus.LIQUIDATED,
            )
        )
        return [
            PositionBalance(
                currency=c, total_value=_decimal(balance) + _decimal(accrued)
            )
            for c, balance, accrued in result.all()
        ]

    async def position_series(
        self, user_id: int, start: date, end: date
    ) -> list[PositionSeries]:
        y = InvestmentYieldModel
        mine = y.position_id.in_(self._user_positions(user_id))
        in_range = select(y.position_id, y.yield_date, y.cumulative_balance).where(
            mine, y.yield_date >= start, y.yield_date <= end
        )
        # El último rendimiento antes del rango, para arrastrar su valor desde `start`.
        seed = (
            select(y.position_id, func.max(y.yield_date).label("day"))
            .where(mine, y.yield_date < start)
            .group_by(y.position_id)
            .subquery()
        )
        seeds = select(y.position_id, y.yield_date, y.cumulative_balance).join(
            seed, and_(y.position_id == seed.c.position_id, y.yield_date == seed.c.day)
        )
        rows = (await self.db.execute(seeds.union_all(in_range))).all()
        if not rows:
            return []
        points: dict[int, list[tuple[date, Decimal]]] = {}
        for pid, day, value in sorted(rows, key=lambda r: (r[0], r[1])):
            points.setdefault(pid, []).append((day, _decimal(value)))

        info = (
            await self.db.execute(
                select(
                    InvestmentPositionModel.id,
                    InvestmentPositionModel.currency,
                    InvestmentPositionModel.status,
                    select(func.max(y.yield_date))
                    .where(y.position_id == InvestmentPositionModel.id)
                    .scalar_subquery(),
                ).where(InvestmentPositionModel.id.in_(list(points)))
            )
        ).all()
        return [
            PositionSeries(
                position_id=pid,
                currency=currency,
                status=status,
                last_yield_date=last,
                points=points[pid],
            )
            for pid, currency, status, last in info
        ]

    async def snapshot_totals(
        self, user_id: int, start: date, end: date
    ) -> list[SnapshotDayTotal]:
        s = HoldingSnapshotModel
        result = await self.db.execute(
            select(
                s.snapshot_date,
                func.coalesce(func.sum(s.market_value_mxn), 0),
                func.sum(case((s.market_value_mxn.is_(None), 1), else_=0)),
            )
            .join(SecurityHoldingModel, SecurityHoldingModel.id == s.holding_id)
            .where(
                SecurityHoldingModel.user_id == user_id,
                and_(s.snapshot_date >= start, s.snapshot_date <= end),
            )
            .group_by(s.snapshot_date)
            .order_by(s.snapshot_date)
        )
        return [
            SnapshotDayTotal(day=day, value_mxn=_decimal(total), unvalued=int(missing))
            for day, total, missing in result.all()
        ]

    async def holding_coverage(self, user_id: int) -> list[HoldingCoverage]:
        h = SecurityHoldingModel
        result = await self.db.execute(
            select(
                h.opened_at,
                h.status,
                h.closed_at,
                h.snapshots_through,
                h.snapshots_dirty_from,
            ).where(h.user_id == user_id)
        )
        return [
            HoldingCoverage(
                opened_at=opened,
                closed_at=closed if status is HoldingStatus.CLOSED else None,
                snapshots_through=through,
                snapshots_dirty_from=dirty,
            )
            for opened, status, closed, through, dirty in result.all()
        ]
