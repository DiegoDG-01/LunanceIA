from decimal import Decimal
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class TransferResponse(BaseModel):
    transfer_uuid: str
    amount: Decimal
    transfer_date: date
    description: Optional[str]
    source_account_name: str
    source_account_uuid: str
    destination_account_name: str
    destination_account_uuid: str
    creation_date: datetime