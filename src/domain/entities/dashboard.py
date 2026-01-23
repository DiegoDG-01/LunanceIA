from dataclasses import dataclass


@dataclass
class DashboardSummary:
    total_spent: float
    total_income: float
    total_purchases: int
    top_category: str
    top_account: str
    today_transactions: list
    category_distribution: list
