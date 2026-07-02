from decimal import Decimal
from typing import Optional
from datetime import date

from pydantic import Field, BaseModel


class CreateTransferRequest(BaseModel):
    source_account_uuid: str = Field(..., description="UUID de la cuenta de origen")
    destination_account_uuid: str = Field(..., description="UUID de la cuenta de destino")
    amount: Decimal = Field(..., gt=Decimal("0"),  description="Monto a transferir")
    description: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=250)
    transfer_date: Optional[date] = Field(None, description="Fecha de la transferencia")