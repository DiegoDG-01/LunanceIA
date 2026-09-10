from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class SavingGoalResponse(BaseModel):
    uuid: str
    account_uuid: str
    account_name: str
    name: str
    target_amount: Decimal
    current_amount: Decimal
    progress_percentage: float
    target_date: date | None = None
    description: str | None = None
    is_active: bool = True
    completion_date: date | None = None
    creation_date: datetime
