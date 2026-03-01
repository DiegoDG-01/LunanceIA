from pydantic import BaseModel, ConfigDict
from typing import Optional
from decimal import Decimal
from datetime import date
from domain.objects.enums import Frequency, TransactionStatus


class SubscriptionResponse(BaseModel):
    uuid: str
    name: str
    account_name: str
    account_uuid: str
    category_name: Optional[str]
    frequency: Frequency
    amount: Decimal
    billing_day: int
    description: Optional[str]
    service_url: Optional[str]
    start_date: date
    end_date: Optional[date]
    is_active: bool


class SubscriptionChargeDetailResponse(BaseModel):
    charge_id: str
    subscription_name: str
    charge_date: date
    charge_amount: Decimal
    charge_status: TransactionStatus

    transaction_id: Optional[str]
    transaction_amount: Decimal
    transaction_description: Optional[str]

    category_name: Optional[str]
    account_name: str

    model_config = ConfigDict(from_attributes=True)
