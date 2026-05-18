from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime, date
from typing import Optional, List

from domain.objects.enums import InstallmentType


class InstallmentChargeResponse(BaseModel):
    uuid: str
    installment_number: int
    amount: Decimal
    due_date: date
    paid: bool
    paid_at: Optional[datetime]


class InstallmentPurchaseResponse(BaseModel):
    uuid: str
    account_uuid: str
    category_id: Optional[int]
    description: str
    total_amount: Decimal
    num_installments: int
    installment_type: InstallmentType
    annual_interest_rate: Decimal
    monthly_payment: Decimal
    purchase_date: date
    notes: Optional[str]
    is_active: bool
    creation_date: datetime
    charges: List[InstallmentChargeResponse]
