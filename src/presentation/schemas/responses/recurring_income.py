from pydantic import BaseModel, ConfigDict
from typing import Optional
from decimal import Decimal
from datetime import date, datetime

from domain.objects.enums import Frequency, TransactionStatus


class RecurringIncomeResponse(BaseModel):
    uuid: str
    name: str
    account_uuid: Optional[str]
    account_name: Optional[str]
    category_name: Optional[str]
    frequency: Frequency
    amount: Decimal
    currency: str
    start_date: date
    end_date: Optional[date]
    next_payment_date: date
    is_active: bool
    description: Optional[str]
    creation_date: datetime


class IncomeDepositResponse(BaseModel):
    uuid: str
    deposit_date: date
    amount: Decimal
    currency: str
    status: TransactionStatus
    transaction_uuid: Optional[str]

    model_config = ConfigDict(from_attributes=True)
