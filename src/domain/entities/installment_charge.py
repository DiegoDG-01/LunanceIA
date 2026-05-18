from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from datetime import timezone


@dataclass
class InstallmentCharge:
    id: Optional[int]
    uuid: Optional[str]
    installment_purchase_id: int
    installment_number: int
    amount: Decimal
    due_date: date
    paid: bool
    transaction_id: Optional[int] = None
    paid_at: Optional[datetime] = None
    creation_date: Optional[datetime] = None

    @classmethod
    def create_new(
        cls,
        installment_purchase_id: int,
        installment_number: int,
        amount: Decimal,
        due_date: date,
    ) -> "InstallmentCharge":
        return cls(
            id=None,
            uuid=None,
            installment_purchase_id=installment_purchase_id,
            installment_number=installment_number,
            amount=amount,
            due_date=due_date,
            paid=False,
            transaction_id=None,
            paid_at=None,
            creation_date=datetime.now(timezone.utc),
        )

    def mark_as_paid(self, transaction_id: int) -> None:
        self.paid = True
        self.transaction_id = transaction_id
        self.paid_at = datetime.now(timezone.utc)
