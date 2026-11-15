from dataclasses import dataclass

from application.securities.queries.portfolio import PortfolioSummary


@dataclass
class DashboardSummary:
    total_spent: float
    total_income: float
    total_purchases: int
    top_category: str
    top_account: str
    today_transactions: list
    category_distribution: list
    # Patrimonio en pesos: cuentas + apartados + acciones.
    net_worth: PortfolioSummary | None = None


@dataclass
class MonthlyBudgetSummary:
    limit: float
    spent: float
    remaining: float


@dataclass
class MobileDashboardSummary:
    total_spent: float
    top_category: str
    category_distribution: list
    monthly_budget: MonthlyBudgetSummary | None
    net_worth: PortfolioSummary | None = None
