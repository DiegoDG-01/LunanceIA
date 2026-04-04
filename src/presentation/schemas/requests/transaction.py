from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import date
from typing import Optional

from domain.objects.enums import TransactionType


class CreateTransactionRequest(BaseModel):
    """Schema para crear transacción."""

    account_uuid: str = Field(..., description="UUID de la cuenta")
    category_id: Optional[int] = Field(None, gt=0, description="ID de la categoría")
    transaction_type: TransactionType = Field(..., description="Tipo de transacción")
    amount: Decimal = Field(..., gt=Decimal("0"), description="Monto")
    # currency: str = Field("MXN", min_length=3, max_length=3, description="Moneda")
    description: Optional[str] = Field(None, max_length=500, description="Descripción")
    notes: Optional[str] = Field(None, max_length=1000, description="Notas")
    transaction_date: Optional[date] = Field(None, description="Fecha de transacción")


class CreateTransactionFromImageRequest(BaseModel):
    """Schema para crear transacción desde imagen."""

    account_uuid: str = Field(..., description="UUID de la cuenta")


class UpdateTransactionRequest(BaseModel):
    """Schema para request de actualización de transacción."""

    description: Optional[str] = Field(
        None, max_length=500, description="Nueva descripción"
    )
    notes: Optional[str] = Field(None, max_length=1000, description="Nuevas notas")
    category_id: Optional[int] = Field(None, gt=0, description="Nueva categoría")
    transaction_type: Optional[TransactionType] = Field(None, description="Nuevo tipo")
    amount: Optional[Decimal] = Field(None, gt=Decimal("0"), description="Nuevo monto")
    transaction_date: Optional[date] = Field(None, description="Nueva fecha")
    account_uuid: Optional[str] = Field(None, description="UUID de la cuenta")

    class Config:
        json_schema_extra = {
            "example": {
                "description": "Groceries - Updated",
                "notes": "Weekly shopping at new store",
                "category_id": 2,
                "transaction_type": "EXPENSE",
                "amount": 125.50,
                "transaction_date": "2024-01-16",
                "account_uuid": "some-uuid",
            }
        }


class TransactionFilterRequest(BaseModel):
    """Schema para filtrar transacciones."""

    account_id: Optional[int] = Field(None, gt=0, description="ID de la cuenta")
    category_id: Optional[int] = Field(None, gt=0, description="ID de la categoría")
    type: Optional[TransactionType] = Field(None, description="Tipo de transacción")
    start_date: Optional[date] = Field(None, description="Fecha de inicio")
    end_date: Optional[date] = Field(None, description="Fecha de fin")
    limit: int = Field(100, ge=1, le=1000, description="Límite de resultados")
    offset: int = Field(0, ge=0, description="Offset para paginación")
