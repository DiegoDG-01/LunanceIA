from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class TransferResponse(BaseModel):
    transfer_uuid: str
    amount: Decimal
    currency: str = Field(..., description="Moneda de la cuenta: MXN, USD o EUR")
    transfer_date: date
    description: str | None
    source_account_name: str
    source_account_uuid: str
    destination_account_name: str
    destination_account_uuid: str
    creation_date: datetime
