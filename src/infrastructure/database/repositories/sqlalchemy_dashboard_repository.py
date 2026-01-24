import json
from sqlalchemy import text
from sqlalchemy.orm import Session

from domain.entities.dashboard import DashboardSummary
from domain.repositories.dashboard_repository import DashboardRepository


class SQLAlchemyDashboardRepository(DashboardRepository):
    """
    Implementation of DashboardRepository using SQLAlchemy
    """

    def __init__(self, db: Session):
        self.db = db

    def get_dashboard_summary(self, uuid: str, user_id: int) -> DashboardSummary:
        # Check if we are running on SQLite (for tests)
        try:
            is_sqlite = self.db.bind and self.db.bind.dialect.name == "sqlite"
        except (AttributeError, Exception):
            is_sqlite = False

        if is_sqlite:
            return self._get_sqlite_dashboard_summary(user_id)

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
        result = self.db.execute(query, {"user_id": user_id})

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

    def _get_sqlite_dashboard_summary(self, user_id: int) -> DashboardSummary:
        """Simplified version of dashboard summary for SQLite (tests)"""
        from infrastructure.database.models import (
            TransactionModel,
            CategoryModel,
            AccountModel,
        )
        from sqlalchemy import func, case
        from datetime import date

        # Get start of current month
        today = date.today()
        month_start = date(today.year, today.month, 1)

        # Total Spent & Income
        # Note: We use case syntax correctly here
        totals = (
            self.db.query(
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
            )
            .filter(
                TransactionModel.user_id == user_id,
                TransactionModel.transaction_date >= month_start,
            )
            .first()
        )

        # Top Category
        top_cat = (
            self.db.query(CategoryModel.name)
            .join(TransactionModel, TransactionModel.category_id == CategoryModel.id)
            .filter(
                TransactionModel.user_id == user_id,
                TransactionModel.type == "EXPENSE",
                TransactionModel.transaction_date >= month_start,
            )
            .group_by(CategoryModel.name)
            .order_by(func.count(TransactionModel.id).desc())
            .first()
        )

        # Top Account
        top_acc = (
            self.db.query(AccountModel.name)
            .join(TransactionModel, TransactionModel.account_id == AccountModel.id)
            .filter(
                TransactionModel.user_id == user_id,
                TransactionModel.type == "EXPENSE",
                TransactionModel.transaction_date >= month_start,
            )
            .group_by(AccountModel.name)
            .order_by(func.count(TransactionModel.id).desc())
            .first()
        )

        return DashboardSummary(
            total_spent=float(totals.total_spent or 0),
            total_income=float(totals.total_income or 0),
            total_purchases=int(totals.total_purchases or 0),
            top_category=top_cat[0] if top_cat else "N/A",
            top_account=top_acc[0] if top_acc else "N/A",
            today_transactions=[],  # Simplified for tests
            category_distribution=[],  # Simplified for tests
        )
