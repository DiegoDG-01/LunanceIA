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

        query = text("""WITH UserTransactions AS (SELECT t.id,
                                                         t.amount,
                                                         t.type,
                                                         c.name AS category_name,
                                                         a.name AS account_name
                                                  FROM transactions t
                                                           INNER JOIN users u ON t.user_id = u.id
                                                           LEFT JOIN categories c ON t.category_id = c.id
                                                           LEFT JOIN accounts a ON t.account_id = a.id
                                                  WHERE u.uuid = :user_uuid
                                                            AND YEAR(t.creation_date) = :year
                                                            AND MONTH(t.creation_date) = :month
                            )
                           , Totals AS (
                        SELECT
                            COALESCE(SUM(CASE WHEN type = 'EXPENSE' THEN amount ELSE 0 END), 0) AS total_spent,
                            COALESCE(SUM(CASE WHEN type = 'INCOME' THEN amount ELSE 0 END), 0) AS total_income,
                            COUNT(CASE WHEN type = 'EXPENSE' THEN 1 END) AS total_purchases
                        FROM UserTransactions
                            ), TopCategory AS (
                        SELECT category_name
                        FROM UserTransactions
                        WHERE type = 'EXPENSE'
                        GROUP BY category_name
                        ORDER BY COUNT(id) DESC LIMIT 1
                            ),
                            TopAccount AS (
                        SELECT account_name
                        FROM UserTransactions
                        WHERE type = 'EXPENSE'
                        GROUP BY account_name
                        ORDER BY COUNT(id) DESC LIMIT 1
                            )
        SELECT (SELECT total_spent FROM Totals)                         AS total_spent,
               (SELECT total_income FROM Totals)                        AS total_income,
               (SELECT total_purchases FROM Totals)                     AS total_purchases,
               COALESCE((SELECT category_name FROM TopCategory), 'N/A') AS top_category,
               COALESCE((SELECT account_name FROM TopAccount), 'N/A')   AS top_account;""")

        # 3. Secure Execution
        result = self.db.execute(query, {
            "user_uuid": uuid,
            "year": target_year,
            "month": target_month
        })

        row = result.fetchone()

        if row:
            return DashboardSummary(
                total_spent=row.total_spent,
                total_income=row.total_income,
                total_purchases=row.total_purchases,
                top_category=row.top_category,
                top_account=row.top_account
            )

        return None