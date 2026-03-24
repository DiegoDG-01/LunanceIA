from pydantic import BaseModel, Field, field_validator
from decimal import Decimal
from typing import Optional
from datetime import date

from domain.objects.enums import AccountType
from shared.exceptions.domain import InvalidAccountSettingsError


class CreditCardSettingsRequest(BaseModel):
    billing_cycle_day: int = Field(..., ge=1, le=31, description="Dias de facturacion")
    payment_due_day: int = Field(..., ge=1, le=31, description="Dias de pago")
    credit_limit: Optional[Decimal] = Field(None, ge=0, description="Limite de credito")
    minimum_payment_percentage: Optional[Decimal] = Field(
        None, ge=0, le=100, description="Porcentaje minimo de pago"
    )


class InvestmentCardSettingsRequest(BaseModel):
    investment_type: str = Field(..., max_length=50)
    investment_rate: Decimal = Field(..., ge=0, description="Tasa de interes")
    lock_period_end_date: Optional[date] = Field(None, description="Fecha de bloqueo")
    maturity_date: Optional[date] = Field(None, description="Fecha de vencimiento")
    early_withdrawal_penalty: Optional[Decimal] = Field(
        None, ge=0, le=100, description="Penalidad por retiro temprano"
    )


class CreateAccountRequest(BaseModel):
    """Schema para crear cuenta."""

    bank_id: Optional[int] = Field(None, description="ID del banco")
    name: str = Field(
        ..., min_length=1, max_length=100, description="Nombre de la cuenta"
    )
    account_type: AccountType = Field(..., description="Tipo de cuenta")
    initial_balance: Decimal = Field(
        Decimal("0.00"), ge=0, description="Balance inicial"
    )
    currency: str = Field("MXN", min_length=3, max_length=3, description="Moneda")
    is_active: bool = Field(True, description="Estado de la cuenta")
    credit_card_settings: Optional[CreditCardSettingsRequest] = None
    investment_settings: Optional[InvestmentCardSettingsRequest] = None

    @field_validator("credit_card_settings")
    @classmethod
    def validate_credit_card_settings(cls, v, values):
        if v and values.data.get("account_type") != AccountType.CREDIT_CARD:
            raise InvalidAccountSettingsError(
                "Credit card settings can only be set for credit cards"
            )
            # raise ValueError("Credit card settings can only be set for credit accounts")
        return v

    @field_validator("investment_settings")
    @classmethod
    def validate_investment_settings(cls, v, values):
        if v and values.data.get("account_type") != AccountType.INVESTMENT:
            raise InvalidAccountSettingsError(
                "Investment settings can only be set for investments"
            )
            # raise ValueError("Investment settings can only be set for investment accounts")
        return v


class UpdateAccountRequest(BaseModel):
    """Schema para actualizar cuenta."""

    bank_id: Optional[int] = Field(None, description="ID del banco")
    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Nombre de la cuenta"
    )
    current_balance: Optional[Decimal] = Field(None, ge=0, description="Balance actual")
    credit_card_settings: Optional[CreditCardSettingsRequest] = None
    investment_settings: Optional[InvestmentCardSettingsRequest] = None


class UpdateAccountSettingsRequest(BaseModel):
    credit_card_settings: Optional[CreditCardSettingsRequest] = None
    investment_settings: Optional[InvestmentCardSettingsRequest] = None


class AccountActivationRequest(BaseModel):
    """Schema para activar/desactivar cuenta."""

    is_active: bool = Field(..., description="Estado de la cuenta")
