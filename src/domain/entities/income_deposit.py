from dataclasses import dataclass
from datetime import datetime, date, timezone
from typing import Optional

from domain.objects.money import Money
from domain.objects.enums import TransactionStatus


@dataclass
class IncomeDeposit:
    id: Optional[int]
    uuid: Optional[str]
    recurring_income_id: int
    deposit_date: date
    amount: Money
    status: TransactionStatus
    transaction_id: Optional[int] = None
    processing_date: Optional[datetime] = None

    @classmethod
    def create_pending(
        cls,
        recurring_income_id: int,
        deposit_date: date,
        amount: Money,
    ):
        return cls(
            id=None,
            uuid=None,
            recurring_income_id=recurring_income_id,
            deposit_date=deposit_date,
            amount=amount,
            status=TransactionStatus.PENDIENTE,
            transaction_id=None,
            processing_date=None,
        )

    def mark_as_paid(self, transaction_id: int):
        self.transaction_id = transaction_id
        self.status = TransactionStatus.PAGADO
        self.processing_date = datetime.now(timezone.utc)

    def mark_as_failed(self):
        self.status = TransactionStatus.FALLIDO
        self.processing_date = datetime.now(timezone.utc)

    def mark_as_cancelled(self):
        self.status = TransactionStatus.CANCELADO
        self.processing_date = datetime.now(timezone.utc)
