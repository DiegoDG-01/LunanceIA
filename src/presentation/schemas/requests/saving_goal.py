from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from datetime import date


class SavingGoalRequest(BaseModel):
    account_uuid: str = Field(..., description="UUID de la cuenta")
    name: str = Field(
        ..., min_length=1, max_length=100, description="Nombre del objetivo de ahorro"
    )
    target_amount: Decimal = Field(..., gt=Decimal("0"), description="Monto objetivo")
    target_date: Optional[date] = Field(None, description="Fecha objetivo")
    description: Optional[str] = Field(
        None, max_length=250, description="Descripción del objetivo"
    )

class UpdateSavingGoalRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    target_amount: Optional[Decimal] = Field(None, gt=Decimal("0"))
    target_date: Optional[date] = Field(None)
    description: Optional[str] = Field(None, max_length=250)
