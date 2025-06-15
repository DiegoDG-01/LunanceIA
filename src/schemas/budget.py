from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

from utils.enums import BudgetPeriod
from .category import Category


class BaseBudget(BaseModel):
    category_id: Optional[int] = None
    name: str
    limit_amount: Decimal = Field(..., decimal_places=2, gt=0)
    period: BudgetPeriod
    start_date: date
    end_date: Optional[date] = None
    is_active: bool = True
    alert_percentage: int = Field(default=80, ge=0, le=100)


class CreateBudget(BaseBudget):
    pass


class UpdateBudget(BaseModel):
    category_id: Optional[int] = None
    name: Optional[str] = None
    limit_amount: Optional[Decimal] = Field(None, decimal_places=2, gt=0)
    period: Optional[BudgetPeriod] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None
    alert_percentage: Optional[int] = Field(None, ge=0, le=100)


class Budget(BaseBudget):
    budget_id: int
    user_id: int
    creation_date: datetime

    model_config = ConfigDict(from_attributes=True)


class DetailBudget(Budget):
    category: Optional[Category] = None
    amount_spent: Decimal = Field(default=Decimal("0.00"))
    percentage_used: float = 0.0
    remaining_days: int = 0