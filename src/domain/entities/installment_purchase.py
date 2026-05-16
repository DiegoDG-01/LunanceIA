from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from domain.objects.enums import InstallmentType
from domain.objects.money import Money


@dataclass
class InstallmentPurchase:
    id: Optional[int]
    uuid: Optional[str]
    user_id: int
    account_id: int
    category_id: Optional[int]
    description: str
    total_amount: Money
    num_installments: int
    installment_type: InstallmentType
    annual_interest_rate: Decimal
    monthly_payment: Decimal
    purchase_date: date
    notes: Optional[str]
    is_active: bool
    creation_date: datetime

    @classmethod
    def create_new(
        cls,
        user_id: int,
        account_id: int,
        category_id: Optional[int],
        description: str,
        total_amount: Money,
        num_installments: int,
        installment_type: InstallmentType,
        annual_interest_rate: Decimal,
        purchase_date: date,
        notes: Optional[str] = None,
    ) -> "InstallmentPurchase":

        monthly_payment = cls._calculate_monthly_payment(
            total_amount.amount,
            num_installments,
            installment_type,
            annual_interest_rate,
        )
        return cls(
            id=None,
            uuid=None,
            user_id=user_id,
            account_id=account_id,
            category_id=category_id,
            description=description,
            total_amount=total_amount,
            num_installments=num_installments,
            installment_type=installment_type,
            annual_interest_rate=annual_interest_rate,
            monthly_payment=monthly_payment,
            purchase_date=purchase_date,
            notes=notes,
            is_active=True,
            creation_date=datetime.now(),
        )

    @staticmethod
    def _calculate_monthly_payment(
        principal: Decimal,
        n: int,
        installment_type: InstallmentType,
        annual_rate: Decimal,
    ) -> Decimal:
        if installment_type == InstallmentType.NO_INTEREST or annual_rate == 0:
            return round(principal / n, 2)

        monthly_rate = annual_rate / Decimal("12") / Decimal("100")
        payment = principal * (monthly_rate * (1 + monthly_rate) ** n) / ((1 + monthly_rate) ** n - 1)
        return round(payment, 2)































