from dataclasses import dataclass, field

from application.securities.queries.portfolio import PortfolioSummary


@dataclass
class MonthlyBudgetSummary:
    limit: float
    spent: float
    remaining: float


@dataclass
class CurrencyDashboard:
    """Lo del mes en una sola moneda: los montos de monedas distintas no se suman."""

    currency: str
    total_spent: float
    total_income: float
    total_purchases: int
    top_category: str
    top_account: str
    today_transactions: list
    category_distribution: list


@dataclass
class DashboardSummary:
    # Los campos de arriba son solo de MXN (compatibilidad); cada moneda está en
    # `by_currency`.
    total_spent: float
    total_income: float
    total_purchases: int
    top_category: str
    top_account: str
    today_transactions: list
    category_distribution: list
    by_currency: list[CurrencyDashboard] = field(default_factory=list)
    # Patrimonio en pesos: cuentas + apartados + acciones.
    net_worth: PortfolioSummary | None = None


@dataclass
class MobileCurrencyDashboard:
    currency: str
    total_spent: float
    top_category: str
    category_distribution: list
    monthly_budget: MonthlyBudgetSummary | None


@dataclass
class MobileDashboardSummary:
    # Solo MXN, como en el web; cada moneda está en `by_currency`.
    total_spent: float
    top_category: str
    category_distribution: list
    monthly_budget: MonthlyBudgetSummary | None
    by_currency: list[MobileCurrencyDashboard] = field(default_factory=list)
    net_worth: PortfolioSummary | None = None
