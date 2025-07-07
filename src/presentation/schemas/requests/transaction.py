from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import date
from typing import Optional

from domain.objects.enums import TransactionType


class CreateTransactionRequest(BaseModel):
    """Schema para crear transacción."""

    account_id: int = Field(..., gt=0, description="ID de la cuenta")
    category_id: int = Field(..., gt=0, description="ID de la categoría")
    type: TransactionType = Field(..., description="Tipo de transacción")
    amount: Decimal = Field(..., gt=0, description="Monto")
    currency: str = Field("MXN", min_length=3, max_length=3, description="Moneda")
    description: Optional[str] = Field(None, max_length=500, description="Descripción")
    notes: Optional[str] = Field(None, max_length=1000, description="Notas")
    transaction_date: Optional[date] = Field(None, description="Fecha de transacción")


class UpdateTransactionRequest(BaseModel):
    """Schema para actualizar transacción."""

    description: Optional[str] = Field(None, max_length=500, description="Descripción")
    notes: Optional[str] = Field(None, max_length=1000, description="Notas")
    category_id: Optional[int] = Field(None, gt=0, description="ID de la categoría")


class TransactionFilterRequest(BaseModel):
    """Schema para filtrar transacciones."""

    account_id: Optional[int] = Field(None, gt=0, description="ID de la cuenta")
    category_id: Optional[int] = Field(None, gt=0, description="ID de la categoría")
    type: Optional[TransactionType] = Field(None, description="Tipo de transacción")
    start_date: Optional[date] = Field(None, description="Fecha de inicio")
    end_date: Optional[date] = Field(None, description="Fecha de fin")
    limit: int = Field(100, ge=1, le=1000, description="Límite de resultados")
    offset: int = Field(0, ge=0, description="Offset para paginación")
