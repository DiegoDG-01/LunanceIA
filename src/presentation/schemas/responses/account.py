from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime, date
from typing import Optional

from domain.objects.enums import AccountType, InterestType


class CreditCardSettingsResponse(BaseModel):
    billing_cycle_day: int = Field(..., description="Dias de facturacion")
    payment_due_day: int = Field(..., description="Dias de pago")
    credit_limit: Optional[Decimal] = Field(None, description="Limite de credito")
    minimum_payment_percentage: Optional[Decimal] = Field(
        None, description="Percentage de credito"
    )

    class Config:
        from_attributes = True
        json_encoders = {Decimal: str}


class InvestmentSettingsResponse(BaseModel):
    investment_type: str
    investment_rate: Decimal
    lock_period_end_date: Optional[date]
    maturity_date: Optional[date]
    early_withdrawal_penalty: Optional[Decimal]
    interest_type: InterestType = InterestType.COMPOUND

    class Config:
        from_attributes = True
        json_encoders = {Decimal: str}


class AccountResponse(BaseModel):
    """Schema de respuesta para cuenta."""

    bank_id: Optional[int] = Field(None, description="ID del banco")
    bank_name: Optional[str] = Field(None, description="Nombre del banco")
    bank_code: Optional[str] = Field(None, description="Codigo del banco")
    account_uuid: str = Field(..., description="Identificador unico de la cuenta")
    name: str = Field(..., description="Nombre de la cuenta")
    account_type: AccountType = Field(..., description="Tipo de cuenta")
    current_balance: Decimal = Field(..., description="Balance actual")
    currency: str = Field(..., description="Moneda")
    is_active: bool = Field(..., description="Estado de la cuenta")
    credit_card_settings: Optional[CreditCardSettingsResponse] = None
    investment_settings: Optional[InvestmentSettingsResponse] = None

    class Config:
        from_attributes = True
        json_encoders = {Decimal: str}


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
    last_transaction_date: Optional[datetime] = Field(
        None, description="Fecha de última transacción"
    )


class AccountRecentActivityResponse(BaseModel):
    """Schema de respuesta para resumen de cuenta."""

    name: str = Field(..., description="Nombre de la cuenta")
    category_name: str = Field(None, description="Nombre de la categoria")
    amount: Decimal = Field(..., description="Amount")
    transaction_date: date = Field(..., description="Fecha de la cuenta")
