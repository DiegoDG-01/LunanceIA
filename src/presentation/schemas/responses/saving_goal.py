from decimal import Decimal
from typing import Optional
from datetime import date, datetime

from pydantic import BaseModel


class SavingGoalResponse(BaseModel):
    uuid: str
    account_uuid: str
    account_name: str
    name: str
    target_amount: Decimal
    current_amount: Decimal
    progress_percentage: float
    target_date: Optional[date] = None
    description: Optional[str] = None
    is_active: bool = True
    completion_date: Optional[date] = None
    creation_date: datetime