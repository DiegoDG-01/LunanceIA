from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from domain.objects.enums import TransactionType


class CreateTransactionRequest(BaseModel):
    """Schema para crear transacción."""

    account_uuid: str = Field(..., description="UUID de la cuenta")
    category_id: int | None = Field(None, gt=0, description="ID de la categoría")
    transaction_type: TransactionType = Field(..., description="Tipo de transacción")
    amount: Decimal = Field(..., gt=Decimal(0), description="Monto")
    # currency: str = Field("MXN", min_length=3, max_length=3, description="Moneda")
    description: str | None = Field(None, max_length=500, description="Descripción")
    notes: str | None = Field(None, max_length=1000, description="Notas")
    transaction_date: date | None = Field(None, description="Fecha de transacción")


class CreateTransactionFromImageRequest(BaseModel):
    """Schema para crear transacción desde imagen."""

    account_uuid: str = Field(..., description="UUID de la cuenta")


class UpdateTransactionRequest(BaseModel):
    """Schema para request de actualización de transacción."""

    description: str | None = Field(
        None, max_length=500, description="Nueva descripción"
    )
    notes: str | None = Field(None, max_length=1000, description="Nuevas notas")
    category_id: int | None = Field(None, gt=0, description="Nueva categoría")
    transaction_type: TransactionType | None = Field(None, description="Nuevo tipo")
    amount: Decimal | None = Field(None, gt=Decimal(0), description="Nuevo monto")
    transaction_date: date | None = Field(None, description="Nueva fecha")
    account_uuid: str | None = Field(None, description="UUID de la cuenta")

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

    account_id: int | None = Field(None, gt=0, description="ID de la cuenta")
    category_id: int | None = Field(None, gt=0, description="ID de la categoría")
    type: TransactionType | None = Field(None, description="Tipo de transacción")
    start_date: date | None = Field(None, description="Fecha de inicio")
    end_date: date | None = Field(None, description="Fecha de fin")
    limit: int = Field(100, ge=1, le=1000, description="Límite de resultados")
    offset: int = Field(0, ge=0, description="Offset para paginación")
