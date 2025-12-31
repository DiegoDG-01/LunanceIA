import json
from sqlalchemy import text
from sqlalchemy.orm import Session

from domain.entities.dashboard import DashboardSummary
from domain.repositories.dashboard_repository import DashboardRepository

from datetime import datetime


class SQLAlchemyDashboardRepository(DashboardRepository):
    """
    Implementation of DashboardRepository using SQLAlchemy
    """

    def __init__(self, db: Session):
        self.db = db

    def get_dashboard_summary(self, uuid: str) -> DashboardSummary:
        now = datetime.now()
        target_month = now.month
        target_year = now.year

        query = text("""WITH DateConfig AS (
    SELECT
        DATE_FORMAT(NOW(), '%Y-%m-01 00:00:00') AS month_start,
        DATE_FORMAT(NOW() + INTERVAL 1 MONTH, '%Y-%m-01 00:00:00') AS month_end,
        CURDATE() AS today_end,
        CURDATE() - INTERVAL 7 DAY AS today_start
),
MonthTotals AS (
    SELECT
        COALESCE(SUM(CASE WHEN type = 'EXPENSE' THEN amount ELSE 0 END), 0) AS total_spent,
        COALESCE(SUM(CASE WHEN type = 'INCOME' THEN amount ELSE 0 END), 0) AS total_income,
        COUNT(CASE WHEN type = 'EXPENSE' THEN 1 END) AS total_purchases
    FROM transactions t
    CROSS JOIN DateConfig dc
    WHERE t.user_id = :user_id
      AND t.creation_date >= dc.month_start
      AND t.creation_date < dc.month_end
),
TopCategory AS (
    SELECT c.name AS category_name
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
TopAccount AS (
    SELECT a.name AS account_name
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
TodayTransactions AS (
    SELECT JSON_ARRAYAGG(
        JSON_OBJECT(
            'date', t.transaction_date,
            'amount', t.amount,
            'category', COALESCE(c.name, 'Sin Categoría'),
            'account', COALESCE(a.name, 'Sin Cuenta')
        )
    ) AS json_data
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
)
SELECT
    (SELECT total_spent FROM MonthTotals) AS total_spent,
    (SELECT total_income FROM MonthTotals) AS total_income,
    (SELECT total_purchases FROM MonthTotals) AS total_purchases,
    COALESCE((SELECT category_name FROM TopCategory), 'N/A') AS top_category,
    COALESCE((SELECT account_name FROM TopAccount), 'N/A') AS top_account,
    COALESCE((SELECT json_data FROM TodayTransactions), JSON_ARRAY()) AS today_transactions;""")

        # 3. Secure Execution
        result = self.db.execute(query, {
            "user_id": 1
        })

        row = result.fetchone()

        if row:
            return DashboardSummary(
                total_spent=row.total_spent,
                total_income=row.total_income,
                total_purchases=row.total_purchases,
                top_category=row.top_category,
                top_account=row.top_account,
                today_transactions=json.loads(row.today_transactions) if row.today_transactions else []
            )

        return None