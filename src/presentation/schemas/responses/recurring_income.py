from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from domain.objects.enums import Frequency, TransactionStatus


class RecurringIncomeResponse(BaseModel):
    uuid: str
    name: str
    account_uuid: str | None
    account_name: str | None
    category_name: str | None
    frequency: Frequency
    amount: Decimal
    currency: str
    start_date: date
    end_date: date | None
    next_payment_date: date
    is_active: bool
    description: str | None
    creation_date: datetime


class IncomeDepositResponse(BaseModel):
    uuid: str
    deposit_date: date
    amount: Decimal
    currency: str
    status: TransactionStatus
    transaction_uuid: str | None

    model_config = ConfigDict(from_attributes=True)
