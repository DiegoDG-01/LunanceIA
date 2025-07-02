from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from typing import Optional

from domain.objects.enums import AccountType


class AccountResponse(BaseModel):
    """Schema de respuesta para cuenta."""
    account_id: int = Field(..., description="ID de la cuenta")
    user_id: int = Field(..., description="ID del usuario")
    name: str = Field(..., description="Nombre de la cuenta")
    type: AccountType = Field(..., description="Tipo de cuenta")
    bank: Optional[str] = Field(None, description="Banco")
    current_balance: Decimal = Field(..., description="Balance actual")
    currency: str = Field(..., description="Moneda")
    is_active: bool = Field(..., description="Estado de la cuenta")
    creation_date: datetime = Field(..., description="Fecha de creación")

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: str
        }


class AccountListResponse(BaseModel):
    """Schema de respuesta para lista de cuentas."""
    accounts: list[AccountResponse] = Field(..., description="Lista de cuentas")
    total: int = Field(..., description="Total de cuentas")


class AccountSummaryResponse(BaseModel):
    """Schema de respuesta para resumen de cuenta."""
    account_id: int = Field(..., description="ID de la cuenta")
    name: str = Field(..., description="Nombre de la cuenta")
    current_balance: Decimal = Field(..., description="Balance actual")
    currency: str = Field(..., description="Moneda")
    total_transactions: int = Field(..., description="Total de transacciones")
    last_transaction_date: Optional[datetime] = Field(None, description="Fecha de última transacción")
