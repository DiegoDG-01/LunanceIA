from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional

from domain.objects.money import Money
from domain.objects.enums import TransactionStatus


@dataclass
class SubscriptionCharge:
    id: Optional[int]
    uuid: Optional[str]
    subscription_id: int
    charge_date: date
    amount: Money
    status: TransactionStatus
    transaction_id: Optional[int] = None
    processing_date: Optional[datetime] = None


    @classmethod
    def create_pending(
            cls,
            subscription_id: int,
            charge_date: date,
            amount: Money,
    ):
        return cls(
            id=None,
            uuid=None,
            subscription_id=subscription_id,
            charge_date=charge_date,
            amount=amount,
            status=TransactionStatus.PENDIENTE,
            transaction_id=None,
            processing_date=None,
        )

    def mark_as_paid(self, transaction_id: int):
        self.transaction_id = transaction_id
        self.status = TransactionStatus.PAGADO
        self.processing_date = datetime.now()

    def mark_as_failed(self):
        self.status = TransactionStatus.FALLIDO
        self.processing_date = datetime.now()


    def mark_as_cancelled(self):
        self.status = TransactionStatus.CANCELADO
        self.processing_date = datetime.now()
