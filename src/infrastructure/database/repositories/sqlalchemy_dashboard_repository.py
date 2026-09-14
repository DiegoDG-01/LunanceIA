import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.dashboard import DashboardSummary, MobileDashboardSummary
from domain.repositories.dashboard_repository import DashboardRepository


class SQLAlchemyDashboardRepository(DashboardRepository):
    """
    Implementation of DashboardRepository using SQLAlchemy
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard_summary(self, user_id: int) -> DashboardSummary | None:
        # Check if we are running on SQLite (for tests)
        try:
            is_sqlite = self.db.bind and self.db.bind.dialect.name == "sqlite"
        except (AttributeError, Exception):
            is_sqlite = False

        if is_sqlite:
            return await self._get_sqlite_dashboard_summary(user_id)

        query = text("""WITH DateConfig AS (
    SELECT
        -- Rango para métricas del MES
        DATE_FORMAT(NOW(), '%Y-%m-01 00:00:00') AS month_start,
        DATE_FORMAT(NOW() + INTERVAL 1 MONTH, '%Y-%m-01 00:00:00') AS month_end,
        -- Rango para transacciones de HOY
        CURDATE() - INTERVAL 7 DAY AS today_start,
        CURDATE() + INTERVAL 1 DAY AS today_end
),

-- 1. Totales del Mes
MonthTotals AS (
    SELECT
        COALESCE(SUM(CASE WHEN type = 'EXPENSE' THEN amount ELSE 0 END), 0) AS total_spent,
        COALESCE(SUM(CASE WHEN type = 'INCOME' THEN amount ELSE 0 END), 0)  AS total_income,
        COUNT(CASE WHEN type = 'EXPENSE' THEN 1 END)                        AS total_purchases
    FROM transactions t
    CROSS JOIN DateConfig dc
    WHERE t.user_id = :user_id
      AND t.creation_date >= dc.month_start
      AND t.creation_date < dc.month_end
),

-- 2. Top Categoría (Gastos del Mes)
TopCategory AS (
    SELECT c.name as category_name
    FROM transactions t
    INNER JOIN categories c ON t.category_id = c.id
    CROSS JOIN DateConfig dc
    WHERE t.user_id = :user_id
      AND t.type = 'EXPENSE'
      AND t.creation_date >= dc.month_start
      AND t.creation_date < dc.month_end
    GROUP BY c.name
    ORDER BY COUNT(t.id) DESC
    LIMIT 1
),

-- 3. Top Cuenta (Gastos del Mes)
TopAccount AS (
    SELECT a.name as account_name
    FROM transactions t
    INNER JOIN accounts a ON t.account_id = a.id
    CROSS JOIN DateConfig dc
    WHERE t.user_id = :user_id
      AND t.type = 'EXPENSE'
      AND t.creation_date >= dc.month_start
      AND t.creation_date < dc.month_end
    GROUP BY a.name
    ORDER BY COUNT(t.id) DESC
    LIMIT 1
),

-- 4. Distribución por Categorías (para gráfica de porcentajes)
CategoryDistribution AS (
    SELECT
        c.name as category_name,
        COUNT(t.id) as transaction_count,
#         COALESCE(SUM(t.amount), 0) as total_amount,
        ROUND(COUNT(t.id) * 100.0 / NULLIF(SUM(COUNT(t.id)) OVER(), 0), 2) as percentage_by_count
#         ROUND(SUM(t.amount) * 100.0 / NULLIF(SUM(SUM(t.amount)) OVER(), 0), 2) as percentage_by_amount
    FROM transactions t
    INNER JOIN categories c ON t.category_id = c.id
    CROSS JOIN DateConfig dc
    WHERE t.user_id = :user_id
      AND t.type = 'EXPENSE'
      AND t.creation_date >= dc.month_start
      AND t.creation_date < dc.month_end
    GROUP BY c.id, c.name
    ORDER BY transaction_count DESC
),

-- 5. Convertir distribución a JSON
CategoryDistributionJSON AS (
    SELECT JSON_ARRAYAGG(
        JSON_OBJECT(
            'category', category_name,
            'count', transaction_count,
#             'amount', total_amount,
            'percent_by_count', percentage_by_count
#             'percent_by_amount', percentage_by_amount
        )
    ) as json_data
    FROM CategoryDistribution
),

-- 6. Lista de Transacciones de los últimos 7 días (JSON)
TodayTransactions AS (
    SELECT JSON_ARRAYAGG(
        JSON_OBJECT(
            'date', t.transaction_date,
            'amount', t.amount,
            'category', COALESCE(c.name, 'Sin Categoría'),
            'account', COALESCE(a.name, 'Sin Cuenta')
        )
    ) as json_data
    FROM (
        SELECT * FROM transactions
        WHERE user_id = :user_id
        ORDER BY creation_date DESC
    ) t
    CROSS JOIN DateConfig dc
    LEFT JOIN categories c ON t.category_id = c.id
    LEFT JOIN accounts a ON t.account_id = a.id
    WHERE t.creation_date >= dc.today_start
      AND t.creation_date < dc.today_end
      AND t.type = 'EXPENSE'
)

-- 7. Selección Final
SELECT
    (SELECT total_spent FROM MonthTotals)                    AS total_spent,
    (SELECT total_income FROM MonthTotals)                   AS total_income,
    (SELECT total_purchases FROM MonthTotals)                AS total_purchases,
    COALESCE((SELECT category_name FROM TopCategory), 'N/A') AS top_category,
    COALESCE((SELECT account_name FROM TopAccount), 'N/A')   AS top_account,
    COALESCE((SELECT json_data FROM CategoryDistributionJSON), JSON_ARRAY()) AS category_distribution,
    COALESCE((SELECT json_data FROM TodayTransactions), JSON_ARRAY()) AS today_transactions;""")

        # 3. Secure Execution
        result = await self.db.execute(query, {"user_id": user_id})

        row = result.fetchone()

        if row:
            return DashboardSummary(
                total_spent=row.total_spent,
                total_income=row.total_income,
                total_purchases=row.total_purchases,
                top_category=row.top_category,
                top_account=row.top_account,
                today_transactions=json.loads(row.today_transactions)
                if row.today_transactions
                else [],
                category_distribution=json.loads(row.category_distribution)
                if row.category_distribution
                else [],
            )

        return None

    async def get_mobile_dashboard_summary(
        self, user_id: int
    ) -> MobileDashboardSummary | None:
        try:
            is_sqlite = self.db.bind and self.db.bind.dialect.name == "sqlite"
        except (AttributeError, Exception):
            is_sqlite = False

        if is_sqlite:
            return await self._get_sqlite_mobile_dashboard_summary(user_id)

        query = text("""
        WITH CategoryMetrics AS (
      SELECT
          COALESCE(c.name, 'Sin categoría') AS category,
          COUNT(t.id) AS transaction_count,
          SUM(t.amount) AS total_amount,
          ROUND(
              COUNT(t.id) * 100.0 / NULLIF(SUM(COUNT(t.id)) OVER (), 0),
              2
          ) AS percentage_by_count
      FROM transactions t
      LEFT JOIN categories c ON c.id = t.category_id
      WHERE t.user_id = :user_id
        AND t.type = 'EXPENSE'
        AND t.transaction_date >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
        AND t.transaction_date < DATE_FORMAT(
            CURDATE() + INTERVAL 1 MONTH,
            '%Y-%m-01'
        )
      GROUP BY c.id, c.name
  )
  SELECT
      COALESCE(SUM(total_amount), 0) AS total_spent,
      COALESCE(
          (
              SELECT category
              FROM CategoryMetrics
              ORDER BY transaction_count DESC, category ASC
              LIMIT 1
          ),
          'N/A'
      ) AS top_category,
      COALESCE(
          JSON_ARRAYAGG(
              JSON_OBJECT(
                  'category', category,
                  'count', transaction_count,
                  'percent_by_count', percentage_by_count
              )
          ),
          JSON_ARRAY()
      ) AS category_distribution
  FROM CategoryMetrics;""")

        result = await self.db.execute(query, {"user_id": user_id})

        row = result.fetchone()

        if row:
            return MobileDashboardSummary(
                total_spent=row.total_spent,
                top_category=row.top_category,
                category_distribution=json.loads(row.category_distribution)
                if row.category_distribution
                else [],
            )

        return None

    async def _get_sqlite_mobile_dashboard_summary(
        self, user_id: int
    ) -> MobileDashboardSummary:
        """SQLite equivalent of the mobile dashboard aggregate for tests."""
        from datetime import date

        from sqlalchemy import func, select

        from infrastructure.database.models import CategoryModel, TransactionModel

        today = date.today()
        month_start = date(today.year, today.month, 1)
        if today.month == 12:
            next_month_start = date(today.year + 1, 1, 1)
        else:
            next_month_start = date(today.year, today.month + 1, 1)

        category_name = func.coalesce(CategoryModel.name, "Sin categoría")
        transaction_count = func.count(TransactionModel.id)
        total_amount = func.coalesce(func.sum(TransactionModel.amount), 0)
        statement = (
            select(
                category_name.label("category"),
                transaction_count.label("count"),
                total_amount.label("total_amount"),
            )
            .select_from(TransactionModel)
            .outerjoin(CategoryModel, TransactionModel.category_id == CategoryModel.id)
            .where(
                TransactionModel.user_id == user_id,
                TransactionModel.type == "EXPENSE",
                TransactionModel.transaction_date >= month_start,
                TransactionModel.transaction_date < next_month_start,
            )
            .group_by(CategoryModel.id, CategoryModel.name)
            .order_by(transaction_count.desc(), category_name.asc())
        )
        rows = (await self.db.execute(statement)).all()

        total_transactions = sum(row.count for row in rows)
        category_distribution = [
            {
                "category": row.category,
                "count": row.count,
                "percent_by_count": round(row.count * 100.0 / total_transactions, 2),
            }
            for row in rows
        ]

        return MobileDashboardSummary(
            total_spent=sum(float(row.total_amount) for row in rows),
            top_category=category_distribution[0]["category"]
            if category_distribution
            else "N/A",
            category_distribution=category_distribution,
        )

    async def _get_sqlite_dashboard_summary(self, user_id: int) -> DashboardSummary:
        """Simplified version of dashboard summary for SQLite (tests)"""
        from datetime import date

        from sqlalchemy import case, func, select

        from infrastructure.database.models import (
            AccountModel,
            CategoryModel,
            TransactionModel,
        )

        # Get start of current month
        today = date.today()
        month_start = date(today.year, today.month, 1)

        # Total Spent & Income
        stmt_totals = select(
            func.sum(
                case(
                    (TransactionModel.type == "EXPENSE", TransactionModel.amount),
                    else_=0,
                )
            ).label("total_spent"),
            func.sum(
                case(
                    (TransactionModel.type == "INCOME", TransactionModel.amount),
                    else_=0,
                )
            ).label("total_income"),
            func.count(case((TransactionModel.type == "EXPENSE", 1))).label(
                "total_purchases"
            ),
        ).where(
            TransactionModel.user_id == user_id,
            TransactionModel.transaction_date >= month_start,
        )
        result_totals = await self.db.execute(stmt_totals)
        totals = result_totals.first()

        # Top Category
        stmt_top_cat = (
            select(CategoryModel.name)
            .join(TransactionModel, TransactionModel.category_id == CategoryModel.id)
            .where(
                TransactionModel.user_id == user_id,
                TransactionModel.type == "EXPENSE",
                TransactionModel.transaction_date >= month_start,
            )
            .group_by(CategoryModel.name)
            .order_by(func.count(TransactionModel.id).desc())
            .limit(1)
        )
        result_top_cat = await self.db.execute(stmt_top_cat)
        top_cat = result_top_cat.first()

        # Top Account
        stmt_top_acc = (
            select(AccountModel.name)
            .join(TransactionModel, TransactionModel.account_id == AccountModel.id)
            .where(
                TransactionModel.user_id == user_id,
                TransactionModel.type == "EXPENSE",
                TransactionModel.transaction_date >= month_start,
            )
            .group_by(AccountModel.name)
            .order_by(func.count(TransactionModel.id).desc())
            .limit(1)
        )
        result_top_acc = await self.db.execute(stmt_top_acc)
        top_acc = result_top_acc.first()

        return DashboardSummary(
            total_spent=float(totals.total_spent or 0) if totals else 0.0,
            total_income=float(totals.total_income or 0) if totals else 0.0,
            total_purchases=int(totals.total_purchases or 0) if totals else 0,
            top_category=top_cat[0] if top_cat else "N/A",
            top_account=top_acc[0] if top_acc else "N/A",
            today_transactions=[],  # Simplified for tests
            category_distribution=[],  # Simplified for tests
        )
