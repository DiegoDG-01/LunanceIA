from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional

from domain.objects.enums import AccountType


class CreateAccountRequest(BaseModel):
    """Schema para crear cuenta."""

    name: str = Field(
        ..., min_length=1, max_length=100, description="Nombre de la cuenta"
    )
    account_type: AccountType = Field(..., description="Tipo de cuenta")
    bank: Optional[str] = Field(None, max_length=100, description="Banco")
    initial_balance: Decimal = Field(
        Decimal("0.00"), ge=0, description="Balance inicial"
    )
    currency: str = Field("MXN", min_length=3, max_length=3, description="Moneda")
    is_active: bool = Field(True, description="Estado de la cuenta")


class UpdateAccountRequest(BaseModel):
    """Schema para actualizar cuenta."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Nombre de la cuenta"
    )
    bank: Optional[str] = Field(None, max_length=100, description="Banco")
    current_balance: Optional[Decimal] = Field(None, ge=0, description="Balance actual")


class AccountActivationRequest(BaseModel):
    """Schema para activar/desactivar cuenta."""

    is_active: bool = Field(..., description="Estado de la cuenta")
