from dataclasses import dataclass
from datetime import UTC, date, datetime

from domain.objects.enums import TransactionStatus
from domain.objects.money import Money


@dataclass
class SubscriptionCharge:
    id: int | None
    uuid: str | None
    subscription_id: int
    charge_date: date
    amount: Money
    status: TransactionStatus
    transaction_id: int | None = None
    processing_date: datetime | None = None

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
        self.processing_date = datetime.now(UTC)

    def mark_as_failed(self):
        self.status = TransactionStatus.FALLIDO
        self.processing_date = datetime.now(UTC)

    def mark_as_cancelled(self):
        self.status = TransactionStatus.CANCELADO
        self.processing_date = datetime.now(UTC)
