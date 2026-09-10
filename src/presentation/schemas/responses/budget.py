from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from domain.objects.enums import BudgetPeriod


class BudgetResponse(BaseModel):
    uuid: str
    name: str
    category_id: int | None
    category_name: str | None
    limit_amount: Decimal
    period: BudgetPeriod
    start_date: date
    end_date: date | None
    is_active: bool
    alert_percentage: int
    creation_date: datetime


class BudgetProgressResponse(BaseModel):
    uuid: str = Field(..., description="UUID del presupuesto")
    name: str = Field(..., description="Nombre del presupuesto")
    category_id: int | None = Field(None, description="ID de categoría (null = todas)")
    category_name: str | None = Field(None, description="Nombre de la categoría")
    limit_amount: Decimal = Field(..., description="Monto límite configurado")
    spent_amount: Decimal = Field(..., description="Total gastado en el periodo actual")
    remaining_amount: Decimal = Field(
        ..., description="Monto restante (puede ser negativo)"
    )
    percentage_used: float = Field(..., description="Porcentaje del límite utilizado")
    alert_percentage: int = Field(..., description="Umbral de alerta configurado (%)")
    is_alert_triggered: bool = Field(
        ..., description="True si el gasto superó el umbral de alerta"
    )
    is_limit_exceeded: bool = Field(
        ..., description="True si el gasto superó el 100% del límite"
    )
    period: BudgetPeriod = Field(..., description="Tipo de periodo del presupuesto")
    period_start: date = Field(..., description="Inicio del periodo actual")
    period_end: date = Field(..., description="Fin del periodo actual")
    is_active: bool = Field(..., description="Estado activo/inactivo del presupuesto")
