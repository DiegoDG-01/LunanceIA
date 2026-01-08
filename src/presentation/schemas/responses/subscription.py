from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import date
from domain.objects.enums import Frequency



class SubscriptionResponse(BaseModel):
    uuid: str
    name: str
    account_name: str
    category_name: Optional[str]
    frequency: Frequency
    amount: Decimal
    billing_day: int
    description: Optional[str]
    service_url: Optional[str]
    start_date: date
    end_date: Optional[date]
    is_active: bool
