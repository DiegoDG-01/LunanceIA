from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from domain.objects.enums import BudgetPeriod


class CreateBudgetRequest(BaseModel):
    name: str = Field(
        ..., min_length=1, max_length=100, description="Nombre del presupuesto"
    )
    limit_amount: Decimal = Field(
        ..., gt=Decimal(0), description="Monto límite del presupuesto"
    )
    period: BudgetPeriod = Field(..., description="Periodicidad del presupuesto")
    start_date: date = Field(..., description="Fecha de inicio del presupuesto")
    category_id: int | None = Field(
        None,
        gt=0,
        description="ID de categoría (opcional — si se omite aplica a todas)",
    )
    end_date: date | None = Field(
        None, description="Fecha de fin del presupuesto (opcional)"
    )
    alert_percentage: int = Field(
        80,
        ge=1,
        le=100,
        description="Porcentaje del límite para activar alerta (1-100)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Comida mensual",
                "limit_amount": 5000.00,
                "period": "mensual",
                "start_date": "2025-05-01",
                "category_id": 1,
                "alert_percentage": 80,
            }
        }
    }


class UpdateBudgetRequest(BaseModel):
    name: str | None = Field(
        None, min_length=1, max_length=100, description="Nombre del presupuesto"
    )
    limit_amount: Decimal | None = Field(
        None, gt=Decimal(0), description="Monto límite del presupuesto"
    )
    period: BudgetPeriod | None = Field(
        None, description="Periodicidad del presupuesto"
    )
    start_date: date | None = Field(None, description="Fecha de inicio")
    end_date: date | None = Field(None, description="Fecha de fin")
    alert_percentage: int | None = Field(
        None, ge=1, le=100, description="Porcentaje para activar alerta (1-100)"
    )
    category_id: int | None = Field(None, gt=0, description="ID de categoría")

    model_config = {
        "json_schema_extra": {
            "example": {
                "limit_amount": 6000.00,
                "alert_percentage": 75,
            }
        }
    }
