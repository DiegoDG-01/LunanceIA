from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from domain.objects.enums import Frequency, TransactionStatus


class SubscriptionResponse(BaseModel):
    uuid: str
    name: str
    account_name: str
    account_uuid: str
    category_name: str | None
    frequency: Frequency
    amount: Decimal
    billing_day: int | None
    description: str | None
    service_url: str | None
    start_date: date
    end_date: date | None
    next_charge_date: date
    is_active: bool


class SubscriptionChargeDetailResponse(BaseModel):
    charge_id: str
    subscription_name: str
    charge_date: date
    charge_amount: Decimal
    charge_status: TransactionStatus

    transaction_id: str | None
    transaction_amount: Decimal
    transaction_description: str | None

    category_name: str | None
    account_name: str

    model_config = ConfigDict(from_attributes=True)


class SubscriptionLastChargeResponse(BaseModel):
    name: str = Field(..., description="Nombre de la suscripción")
    account_name: str = Field(..., description="Nombre de la cuenta")
    amount: Decimal = Field(..., description="Cargo")
    charge_date: date = Field(..., description="Fecha del cargo")
