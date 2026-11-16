from pydantic import BaseModel, Field

from presentation.schemas.responses.security import PortfolioSummaryResponse


class CategoryDistributionResponse(BaseModel):
    category: str = Field(..., description="The category name")
    count: int = Field(..., description="The count of items in the category")
    percent_by_count: float = Field(
        ..., description="The percentage of items in the category by count"
    )


class TodayTransactionResponse(BaseModel):
    date: str = Field(..., description="The date of the transaction")
    amount: float = Field(..., description="The amount of the transaction")
    currency: str = Field("MXN", description="Currency of the account: MXN, USD or EUR")
    category: str = Field(..., description="The category of the transaction")
    account: str = Field(..., description="The account of the transaction")


class CurrencyDashboardResponse(BaseModel):
    currency: str = Field(..., description="MXN, USD or EUR")
    total_spent: float
    total_income: float
    total_purchases: int
    top_category: str
    top_account: str
    today_transactions: list[TodayTransactionResponse]
    category_distribution: list[CategoryDistributionResponse]


class DashboardSummaryResponse(BaseModel):
    # Los campos de arriba son solo MXN; cada moneda viene en `by_currency`.
    total_spent: float = Field(..., description="The total amount spent")
    total_income: float = Field(..., description="The total amount of income")
    total_purchases: int = Field(..., description="The total number of purchases")
    top_category: str = Field(..., description="The top category")
    top_account: str = Field(..., description="The top account")
    today_transactions: list[TodayTransactionResponse] = Field(
        ..., description="The transactions of the day"
    )
    category_distribution: list[CategoryDistributionResponse] = Field(
        ..., description="The distribution of categories"
    )
    by_currency: list[CurrencyDashboardResponse] = Field(
        default_factory=list,
        description="The same totals for each currency with activity; never added together",
    )
    net_worth: PortfolioSummaryResponse | None = Field(
        None, description="Net worth in MXN: accounts, investment positions and stocks"
    )


class MonthlyBudgetSummaryResponse(BaseModel):
    limit: float
    spent: float
    remaining: float


class MobileCurrencyDashboardResponse(BaseModel):
    currency: str
    total_spent: float
    top_category: str
    category_distribution: list[CategoryDistributionResponse]
    monthly_budget: MonthlyBudgetSummaryResponse | None


class MobileDashboardSummaryResponse(BaseModel):
    # Solo MXN; cada moneda viene en `by_currency`.
    total_spent: float
    top_category: str
    category_distribution: list[CategoryDistributionResponse]
    monthly_budget: MonthlyBudgetSummaryResponse | None
    by_currency: list[MobileCurrencyDashboardResponse] = Field(default_factory=list)
    net_worth: PortfolioSummaryResponse | None = None
