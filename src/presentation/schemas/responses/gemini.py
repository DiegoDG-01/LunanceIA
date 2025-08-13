import datetime

from pydantic import BaseModel
from typing import Optional


class GeminiReceipt(BaseModel):
    type: str
    amount: float
    transaction_date: datetime.date
    description: str
    notes: Optional[str]
    category_id: Optional[str] = None


class GeminiErrorResponse(BaseModel):
    error: bool
    reason: str
