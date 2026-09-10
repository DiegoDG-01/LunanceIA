from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from domain.objects.enums import Frequency


class CreateSubscriptionRequest(BaseModel):
    account_uuid: str = Field(..., description="UUID de la cuenta")
    category_id: int = Field(..., gt=0, description="ID de la categoria")
    name: str = Field(
        ..., min_length=1, max_length=100, description="Nombre de la subscripción"
    )
    amount: Decimal = Field(..., gt=Decimal(0), description="Monto de la suscripción")
    frequency: Frequency = Field(..., description="Frecuencia de pago")
    start_date: date = Field(..., description="Fecha de inicio")
    end_date: date | None = Field(None, description="Fecha de fin (opcional)")
    billing_day: int | None = Field(
        None, ge=1, le=31, description="Día de cobro del mes (1-31)"
    )
    description: str | None = Field(None, max_length=500, description="Descripción")
    service_url: str | None = Field(
        None, max_length=255, description="URL del servicio"
    )


class UpdateSubscriptionRequest(BaseModel):
    """Schema para actualizar suscripción."""

    account_uuid: str = Field(..., description="UUID de la cuenta")
    name: str | None = Field(
        None, min_length=1, max_length=100, description="Nombre de la suscripción"
    )
    amount: Decimal | None = Field(None, gt=Decimal(0), description="Monto")
    frequency: Frequency | None = Field(None, description="Frecuencia de pago")
    start_date: date | None = Field(None, description="Fecha de inicio")
    end_date: date | None = Field(None, description="Fecha de fin")
    billing_day: int | None = Field(
        None, ge=1, le=31, description="Día de cobro del mes (1-31)"
    )
    is_active: bool | None = Field(None, description="Estado activo/inactivo")
    description: str | None = Field(None, max_length=500, description="Descripción")
    service_url: str | None = Field(
        None, max_length=255, description="URL del servicio"
    )
    category_id: int | None = Field(None, gt=0, description="ID de la categoría")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Netflix Premium",
                "amount": 299.00,
                "frequency": "MONTHLY",
                "is_active": True,
            }
        }
