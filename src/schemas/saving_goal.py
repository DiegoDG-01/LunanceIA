from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

from .account import Account


class BaseSavingGoal(BaseModel):
    account_id: Optional[int] = None
    name: str
    target_amount: Decimal = Field(..., decimal_places=2, gt=0)
    current_amount: Decimal = Field(default=Decimal("0.00"), decimal_places=2, ge=0)
    target_date: Optional[date] = None
    descripction: Optional[str] = None
    is_active: bool = True


class CreateSavingGoal(BaseSavingGoal):
    pass


class UpdateSavingGoal(BaseModel):
    account_id: Optional[int] = None
    name: Optional[str] = None
    target_amount: Optional[Decimal] = Field(None, decimal_places=2, gt=0)
    current_amount: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    target_date: Optional[date] = None
    descrition: Optional[str] = None
    is_active: Optional[bool] = None


class SavingGoal(BaseSavingGoal):
    goal_id: int
    user_id: int
    creation_date: datetime
    completion_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)


class SavingGoalDetail(SavingGoal):
    account: Optional[Account] = None
    percentage_completed: float = 0.0
    days_to_goal: Optional[int] = None
    required_monthly_amount: Optional[Decimal] = None
