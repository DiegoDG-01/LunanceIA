from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal


@dataclass
class InstallmentCharge:
    id: int | None
    uuid: str | None
    installment_purchase_id: int
    installment_number: int
    amount: Decimal
    due_date: date
    paid: bool
    transaction_id: int | None = None
    paid_at: datetime | None = None
    creation_date: datetime | None = None

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
            creation_date=datetime.now(UTC),
        )

    def mark_as_paid(self, transaction_id: int) -> None:
        self.paid = True
        self.transaction_id = transaction_id
        self.paid_at = datetime.now(UTC)
