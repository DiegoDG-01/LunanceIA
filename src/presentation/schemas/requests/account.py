from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from domain.objects.enums import AccountType
from shared.exceptions.domain import InvalidAccountSettingsError


class CreditCardSettingsRequest(BaseModel):
    billing_cycle_day: int = Field(..., ge=1, le=31, description="Dias de facturacion")
    payment_due_day: int = Field(..., ge=1, le=31, description="Dias de pago")
    credit_limit: Decimal = Field(..., ge=Decimal(0), description="Limite de credito")
    minimum_payment_percentage: Decimal = Field(
        ..., ge=Decimal(0), le=Decimal(100), description="Porcentaje minimo de pago"
    )


class CreateAccountRequest(BaseModel):
    """Schema para crear cuenta."""

    bank_id: int = Field(..., description="ID del banco")
    name: str = Field(
        ..., min_length=1, max_length=100, description="Nombre de la cuenta"
    )
    account_type: AccountType = Field(..., description="Tipo de cuenta")
    initial_balance: Decimal = Field(
        Decimal("0.00"), ge=Decimal(0), description="Balance inicial"
    )
    currency: str = Field("MXN", min_length=3, max_length=3, description="Moneda")
    is_active: bool = Field(True, description="Estado de la cuenta")
    credit_card_settings: CreditCardSettingsRequest | None = None

    @field_validator("credit_card_settings")
    @classmethod
    def validate_credit_card_settings(cls, v, values):
        if v and values.data.get("account_type") != AccountType.CREDIT_CARD:
            raise InvalidAccountSettingsError(
                "Credit card settings can only be set for credit cards"
            )
        return v


class UpdateAccountRequest(BaseModel):
    """Schema para actualizar cuenta."""

    bank_id: int | None = Field(None, description="ID del banco")
    name: str | None = Field(
        None, min_length=1, max_length=100, description="Nombre de la cuenta"
    )
    current_balance: Decimal | None = Field(
        None, ge=Decimal(0), description="Balance actual"
    )
    credit_card_settings: CreditCardSettingsRequest | None = None


class AccountActivationRequest(BaseModel):
    """Schema para activar/desactivar cuenta."""

    is_active: bool = Field(..., description="Estado de la cuenta")
