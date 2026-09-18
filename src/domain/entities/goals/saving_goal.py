from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal


@dataclass
class SavingGoal:
    id: int | None
    uuid: str | None
    user_id: int
    account_id: int
    name: str
    target_amount: Decimal
    target_date: date | None = None
    description: str | None = None
    is_active: bool = True
    completion_date: date | None = None
    creation_date: datetime = None

    @classmethod
    def create_new(
        cls,
        user_id: int,
        account_id: int,
        name: str,
        target_amount: Decimal,
        target_date: date | None = None,
        description: str | None = None,
    ):
        return cls(
            id=None,
            uuid=None,
            user_id=user_id,
            account_id=account_id,
            name=name,
            target_amount=target_amount,
            target_date=target_date,
            description=description,
            is_active=True,
            creation_date=datetime.now(UTC),
        )

    def calculate_progress(self, account_balance: Decimal) -> float:
        if self.target_amount == 0:
            return 0.0
        return float((account_balance / self.target_amount) * 100)

    def is_completed(self, account_balance: Decimal) -> bool:
        return account_balance >= self.target_amount
