from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class SavingGoalRequest(BaseModel):
    account_uuid: str = Field(..., description="UUID de la cuenta")
    name: str = Field(
        ..., min_length=1, max_length=100, description="Nombre del objetivo de ahorro"
    )
    target_amount: Decimal = Field(..., gt=Decimal(0), description="Monto objetivo")
    target_date: date | None = Field(None, description="Fecha objetivo")
    description: str | None = Field(
        None, max_length=250, description="Descripción del objetivo"
    )


class UpdateSavingGoalRequest(BaseModel):
    name: str | None = Field(None, max_length=100)
    target_amount: Decimal | None = Field(None, gt=Decimal(0))
    target_date: date | None = Field(None)
    description: str | None = Field(None, max_length=250)
