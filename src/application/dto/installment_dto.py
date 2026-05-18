from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List

from domain.objects.enums import InstallmentType


@dataclass
class CreateInstallmentPurchaseDTO:
    user_id: int
    account_uuid: str
    category_id: Optional[int]
    description: str
    total_amount: Decimal
    num_installments: int
    installment_type: InstallmentType
    annual_interest_rate: Decimal
    purchase_date: date
    notes: Optional[str] = None
    currency: str = "MXN"


@dataclass
class InstallmentChargeResponseDTO:
    uuid: str
    installment_number: int
    amount: Decimal
    due_date: date
    paid: bool
    paid_at: Optional[datetime]


@dataclass
class InstallmentPurchaseResponseDTO:
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
    charges: List[InstallmentChargeResponseDTO]

    @classmethod
    def from_entity(
        cls, purchase, account_uuid: str, charges: list
    ) -> "InstallmentPurchaseResponseDTO":
        return cls(
            uuid=purchase.uuid,
            account_uuid=account_uuid,
            category_id=purchase.category_id,
            description=purchase.description,
            total_amount=purchase.total_amount.amount,
            num_installments=purchase.num_installments,
            installment_type=purchase.installment_type,
            annual_interest_rate=purchase.annual_interest_rate,
            monthly_payment=purchase.monthly_payment,
            purchase_date=purchase.purchase_date,
            notes=purchase.notes,
            is_active=purchase.is_active,
            creation_date=purchase.creation_date,
            charges=charges,
        )
