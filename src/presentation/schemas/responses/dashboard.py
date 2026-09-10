from pydantic import BaseModel, Field


class CategoryDistributionResponse(BaseModel):
    category: str = Field(..., description="The category name")
    count: int = Field(..., description="The count of items in the category")
    percent_by_count: float = Field(
        ..., description="The percentage of items in the category by count"
    )


class TodayTransactionResponse(BaseModel):
    date: str = Field(..., description="The date of the transaction")
    amount: float = Field(..., description="The amount of the transaction")
    category: str = Field(..., description="The category of the transaction")
    account: str = Field(..., description="The account of the transaction")


class DashboardSummaryResponse(BaseModel):
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
