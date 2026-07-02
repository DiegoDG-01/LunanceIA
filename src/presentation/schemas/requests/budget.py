from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import date
from typing import Optional

from domain.objects.enums import BudgetPeriod


class CreateBudgetRequest(BaseModel):
    name: str = Field(
        ..., min_length=1, max_length=100, description="Nombre del presupuesto"
    )
    limit_amount: Decimal = Field(
        ..., gt=Decimal("0"), description="Monto límite del presupuesto"
    )
    period: BudgetPeriod = Field(..., description="Periodicidad del presupuesto")
    start_date: date = Field(..., description="Fecha de inicio del presupuesto")
    category_id: Optional[int] = Field(
        None, gt=0, description="ID de categoría (opcional — si se omite aplica a todas)"
    )
    end_date: Optional[date] = Field(
        None, description="Fecha de fin del presupuesto (opcional)"
    )
    alert_percentage: int = Field(
        80, ge=1, le=100, description="Porcentaje del límite para activar alerta (1-100)"
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
    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Nombre del presupuesto"
    )
    limit_amount: Optional[Decimal] = Field(
        None, gt=Decimal("0"), description="Monto límite del presupuesto"
    )
    period: Optional[BudgetPeriod] = Field(None, description="Periodicidad del presupuesto")
    start_date: Optional[date] = Field(None, description="Fecha de inicio")
    end_date: Optional[date] = Field(None, description="Fecha de fin")
    alert_percentage: Optional[int] = Field(
        None, ge=1, le=100, description="Porcentaje para activar alerta (1-100)"
    )
    category_id: Optional[int] = Field(None, gt=0, description="ID de categoría")

    model_config = {
        "json_schema_extra": {
            "example": {
                "limit_amount": 6000.00,
                "alert_percentage": 75,
            }
        }
    }
