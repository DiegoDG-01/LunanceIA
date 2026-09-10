from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from domain.objects.enums import Frequency


class CreateRecurringIncomeRequest(BaseModel):
    account_uuid: str = Field(..., description="UUID de la cuenta destino")
    category_id: int = Field(..., gt=0, description="ID de la categoría")
    name: str = Field(
        ..., min_length=1, max_length=100, description="Nombre del ingreso recurrente"
    )
    amount: Decimal = Field(..., gt=Decimal(0), description="Monto del ingreso")
    frequency: Frequency = Field(..., description="Frecuencia del ingreso")
    start_date: date = Field(..., description="Fecha de inicio")
    end_date: date | None = Field(None, description="Fecha de fin (opcional)")
    next_payment_date: date | None = Field(
        None, description="Próxima fecha de pago (default: fecha de inicio)"
    )
    description: str | None = Field(None, max_length=500, description="Descripción")

    class Config:
        json_schema_extra = {
            "example": {
                "account_uuid": "11111111-2222-3333-4444-555555555555",
                "category_id": 3,
                "name": "Nómina Empresa X",
                "amount": 15000.00,
                "frequency": "BIWEEKLY",
                "start_date": "2026-08-01",
            }
        }


class UpdateRecurringIncomeRequest(BaseModel):
    """Schema para actualizar un ingreso recurrente."""

    account_uuid: str | None = Field(None, description="UUID de la cuenta destino")
    name: str | None = Field(
        None, min_length=1, max_length=100, description="Nombre del ingreso"
    )
    amount: Decimal | None = Field(None, gt=Decimal(0), description="Monto")
    frequency: Frequency | None = Field(None, description="Frecuencia del ingreso")
    start_date: date | None = Field(None, description="Fecha de inicio")
    end_date: date | None = Field(None, description="Fecha de fin")
    next_payment_date: date | None = Field(None, description="Próxima fecha de pago")
    is_active: bool | None = Field(None, description="Estado activo/inactivo")
    description: str | None = Field(None, max_length=500, description="Descripción")
    category_id: int | None = Field(None, gt=0, description="ID de la categoría")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Nómina nueva empresa",
                "amount": 18000.00,
                "frequency": "MONTHLY",
            }
        }
