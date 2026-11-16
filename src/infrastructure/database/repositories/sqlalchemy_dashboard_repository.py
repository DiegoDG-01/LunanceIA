"""Resumen del dashboard, separado por moneda.

Una sola implementación para MySQL y SQLite: unas cuantas consultas agrupadas por moneda de la
cuenta y el armado en Python. Antes había SQL crudo de MySQL y una versión aparte para las
pruebas, que además no filtraban igual.

- Web: el mes se cuenta por `creation_date` y los «movimientos recientes» son los gastos de
  los últimos 7 días, igual que el SQL anterior.
- Mobile: el mes se cuenta por `transaction_date`, y el presupuesto mensual suma los
  presupuestos activos de cada moneda llevados a un mes.
"""

from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from application.dashboard.dashboard_repository import DashboardRepository
from application.dashboard.read_models import (
    CurrencyDashboard,
    DashboardSummary,
    MobileCurrencyDashboard,
    MobileDashboardSummary,
    MonthlyBudgetSummary,
)
from domain.objects.enums import BudgetPeriod, Currency, TransactionType
from infrastructure.database.models import (
    AccountModel,
    BudgetModel,
    CategoryModel,
    TransactionModel,
)

BASE_CURRENCY = Currency.MXN.value
NO_CATEGORY = "Sin categoría"
NOT_AVAILABLE = "N/A"
RECENT_DAYS = 7


def _month(today: date) -> tuple[date, date]:
    start = today.replace(day=1)
    end = (start + timedelta(days=32)).replace(day=1)
    return start, end


def _midnight(day: date) -> datetime:
    # `creation_date` se guarda en UTC sin zona.
    return datetime(day.year, day.month, day.day)


def _ordered(currencies: Iterable[str]) -> list[str]:
    known = [c.value for c in Currency]
    return sorted(
        set(currencies), key=lambda c: (known.index(c) if c in known else 99, c)
    )


def _distribution(counts: list[tuple[str, int]]) -> list[dict]:
    """De más a menos movimientos; empates por nombre."""
    total = sum(count for _, count in counts)
    return [
        {
            "category": name,
            "count": count,
            "percent_by_count": round(count * 100.0 / total, 2),
        }
        for name, count in sorted(counts, key=lambda item: (-item[1], item[0]))
    ]


def _top(counts: list[tuple[str, int]]) -> str:
    ranked = _distribution(counts)
    return ranked[0]["category"] if ranked else NOT_AVAILABLE


def _monthly_factors(month_start: date, month_end: date) -> dict[BudgetPeriod, Decimal]:
    """Cuántas veces cabe cada periodo en el mes (las semanas que toca el mes)."""
    last_day = month_end - timedelta(days=1)
    first_week = month_start - timedelta(days=month_start.weekday())
    last_week = last_day - timedelta(days=last_day.weekday())
    return {
        BudgetPeriod.SEMANAL: Decimal((last_week - first_week).days // 7 + 1),
        BudgetPeriod.QUINCENAL: Decimal(2),
        BudgetPeriod.MENSUAL: Decimal(1),
        BudgetPeriod.TRIMESTRAL: Decimal(1) / Decimal(3),
        BudgetPeriod.ANUAL: Decimal(1) / Decimal(12),
    }


class SQLAlchemyDashboardRepository(DashboardRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _today() -> date:
        return datetime.now(UTC).date()

    async def get_dashboard_summary(self, user_id: int) -> DashboardSummary | None:
        today = self._today()
        month_start, month_end = _month(today)
        since, until = _midnight(month_start), _midnight(month_end)
        in_month = (
            TransactionModel.user_id == user_id,
            TransactionModel.creation_date >= since,
            TransactionModel.creation_date < until,
        )
        currency = AccountModel.currency
        is_expense = TransactionModel.type == TransactionType.EXPENSE

        totals = {
            row.currency: row
            for row in await self.db.execute(
                select(
                    currency.label("currency"),
                    func.coalesce(
                        func.sum(case((is_expense, TransactionModel.amount), else_=0)),
                        0,
                    ).label("spent"),
                    func.coalesce(
                        func.sum(
                            case(
                                (
                                    TransactionModel.type == TransactionType.INCOME,
                                    TransactionModel.amount,
                                ),
                                else_=0,
                            )
                        ),
                        0,
                    ).label("income"),
                    func.count(case((is_expense, 1))).label("purchases"),
                )
                .join(AccountModel, AccountModel.id == TransactionModel.account_id)
                .where(*in_month)
                .group_by(currency)
            )
        }

        categories: dict[str, list[tuple[str, int]]] = defaultdict(list)
        for row in await self.db.execute(
            select(currency, CategoryModel.name, func.count(TransactionModel.id))
            .select_from(TransactionModel)
            .join(AccountModel, AccountModel.id == TransactionModel.account_id)
            .join(CategoryModel, CategoryModel.id == TransactionModel.category_id)
            .where(*in_month, is_expense)
            .group_by(currency, CategoryModel.id, CategoryModel.name)
        ):
            categories[row[0]].append((row[1], row[2]))

        accounts: dict[str, list[tuple[str, int]]] = defaultdict(list)
        for row in await self.db.execute(
            select(currency, AccountModel.name, func.count(TransactionModel.id))
            .select_from(TransactionModel)
            .join(AccountModel, AccountModel.id == TransactionModel.account_id)
            .where(*in_month, is_expense)
            .group_by(currency, AccountModel.name)
        ):
            accounts[row[0]].append((row[1], row[2]))

        recent: dict[str, list[dict]] = defaultdict(list)
        for row in await self.db.execute(
            select(
                currency,
                TransactionModel.transaction_date,
                TransactionModel.amount,
                func.coalesce(CategoryModel.name, "Sin Categoría"),
                AccountModel.name,
            )
            .select_from(TransactionModel)
            .join(AccountModel, AccountModel.id == TransactionModel.account_id)
            .outerjoin(CategoryModel, CategoryModel.id == TransactionModel.category_id)
            .where(
                TransactionModel.user_id == user_id,
                is_expense,
                TransactionModel.creation_date
                >= _midnight(today - timedelta(days=RECENT_DAYS)),
                TransactionModel.creation_date < _midnight(today + timedelta(days=1)),
            )
            .order_by(TransactionModel.creation_date.desc(), TransactionModel.id.desc())
        ):
            recent[row[0]].append(
                {
                    "date": row[1].isoformat(),
                    "amount": float(row[2]),
                    "currency": row[0],
                    "category": row[3],
                    "account": row[4],
                }
            )

        by_currency = [
            CurrencyDashboard(
                currency=code,
                total_spent=float(totals[code].spent) if code in totals else 0.0,
                total_income=float(totals[code].income) if code in totals else 0.0,
                total_purchases=int(totals[code].purchases) if code in totals else 0,
                top_category=_top(categories[code]),
                top_account=_top(accounts[code]),
                today_transactions=recent[code],
                category_distribution=_distribution(categories[code]),
            )
            for code in _ordered([*totals, *recent])
        ]
        base = next(
            (c for c in by_currency if c.currency == BASE_CURRENCY),
            CurrencyDashboard(
                BASE_CURRENCY, 0.0, 0.0, 0, NOT_AVAILABLE, NOT_AVAILABLE, [], []
            ),
        )
        return DashboardSummary(
            total_spent=base.total_spent,
            total_income=base.total_income,
            total_purchases=base.total_purchases,
            top_category=base.top_category,
            top_account=base.top_account,
            today_transactions=base.today_transactions,
            category_distribution=base.category_distribution,
            by_currency=by_currency,
        )

    async def get_mobile_dashboard_summary(
        self, user_id: int
    ) -> MobileDashboardSummary | None:
        month_start, month_end = _month(self._today())
        currency = AccountModel.currency
        category = func.coalesce(CategoryModel.name, NO_CATEGORY)

        spent: dict[str, Decimal] = defaultdict(Decimal)
        categories: dict[str, list[tuple[str, int]]] = defaultdict(list)
        for row in await self.db.execute(
            select(
                currency,
                category,
                func.count(TransactionModel.id),
                func.coalesce(func.sum(TransactionModel.amount), 0),
            )
            .select_from(TransactionModel)
            .join(AccountModel, AccountModel.id == TransactionModel.account_id)
            .outerjoin(CategoryModel, CategoryModel.id == TransactionModel.category_id)
            .where(
                TransactionModel.user_id == user_id,
                TransactionModel.type == TransactionType.EXPENSE,
                TransactionModel.transaction_date >= month_start,
                TransactionModel.transaction_date < month_end,
            )
            .group_by(currency, CategoryModel.id, CategoryModel.name)
        ):
            categories[row[0]].append((row[1], row[2]))
            spent[row[0]] += Decimal(str(row[3]))

        factors = _monthly_factors(month_start, month_end)
        limits: dict[str, Decimal] = defaultdict(Decimal)
        for row in await self.db.execute(
            select(
                BudgetModel.currency, BudgetModel.period, BudgetModel.limit_amount
            ).where(BudgetModel.user_id == user_id, BudgetModel.is_active.is_(True))
        ):
            limits[row[0]] += Decimal(str(row[2])) * factors.get(row[1], Decimal(0))

        def budget(code: str) -> MonthlyBudgetSummary | None:
            if code not in limits:
                return None
            limit, used = float(limits[code]), float(spent[code])
            return MonthlyBudgetSummary(limit=limit, spent=used, remaining=limit - used)

        by_currency = [
            MobileCurrencyDashboard(
                currency=code,
                total_spent=float(spent[code]),
                top_category=_top(categories[code]),
                category_distribution=_distribution(categories[code]),
                monthly_budget=budget(code),
            )
            for code in _ordered([*categories, *limits])
        ]
        base = next(
            (c for c in by_currency if c.currency == BASE_CURRENCY),
            MobileCurrencyDashboard(BASE_CURRENCY, 0.0, NOT_AVAILABLE, [], None),
        )
        return MobileDashboardSummary(
            total_spent=base.total_spent,
            top_category=base.top_category,
            category_distribution=base.category_distribution,
            monthly_budget=base.monthly_budget,
            by_currency=by_currency,
        )
