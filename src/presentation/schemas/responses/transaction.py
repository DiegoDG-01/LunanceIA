from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from domain.objects.enums import AccountType, TransactionType


class TransactionResponse(BaseModel):
    uuid: str
    transfer_uuid: str | None
    category: str | None
    transaction_type: TransactionType
    amount: Decimal
    transaction_date: date
    description: str | None
    notes: str | None
    creation_date: datetime
    account_name: str
    account_type: AccountType
    account_uuid: str
