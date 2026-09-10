from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class TransferResponse(BaseModel):
    transfer_uuid: str
    amount: Decimal
    transfer_date: date
    description: str | None
    source_account_name: str
    source_account_uuid: str
    destination_account_name: str
    destination_account_uuid: str
    creation_date: datetime
