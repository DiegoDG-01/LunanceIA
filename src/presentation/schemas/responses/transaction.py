from pydantic import BaseModel
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from domain.objects.enums import TransactionType, AccountType


class TransactionResponse(BaseModel):
    uuid: str
    category: Optional[str]
    transaction_type: TransactionType
    amount: Decimal
    transaction_date: date
    description: Optional[str]
    notes: Optional[str]
    creation_date: datetime
    account_name: str
    account_type: AccountType
    account_uuid: str
