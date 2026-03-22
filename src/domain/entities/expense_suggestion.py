from pydantic import BaseModel


class ExpenseSuggestion(BaseModel):
    category: str
    current_amount: float
    suggested_amount: float
    tip: str


class ExpenseAnalysis(BaseModel):
    suggestions: list[ExpenseSuggestion]
    total_current: float
    total_suggested: float
    summary: str
