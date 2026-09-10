from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from domain.objects.enums import InstallmentType


class InstallmentChargeResponse(BaseModel):
    uuid: str
    installment_number: int
    amount: Decimal
    due_date: date
    paid: bool
    paid_at: datetime | None


class InstallmentPurchaseResponse(BaseModel):
    uuid: str
    account_uuid: str
    category_id: int | None
    description: str
    total_amount: Decimal
    num_installments: int
    installment_type: InstallmentType
    annual_interest_rate: Decimal
    monthly_payment: Decimal
    purchase_date: date
    notes: str | None
    is_active: bool
    creation_date: datetime
    charges: list[InstallmentChargeResponse]
