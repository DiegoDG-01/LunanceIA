from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class CreateTransferRequest(BaseModel):
    source_account_uuid: str = Field(..., description="UUID de la cuenta de origen")
    destination_account_uuid: str = Field(
        ..., description="UUID de la cuenta de destino"
    )
    amount: Decimal = Field(..., gt=Decimal(0), description="Monto a transferir")
    description: str | None = Field(None, max_length=100)
    notes: str | None = Field(None, max_length=250)
    transfer_date: date | None = Field(None, description="Fecha de la transferencia")
