from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional

from domain.objects.enums import Frequency
from domain.objects.frequency import next_occurrence
from domain.objects.money import Money
from shared.exceptions.domain import InvalidIncomeDateRangeError


@dataclass
class RecurringIncome:
    id: Optional[int]
    uuid: Optional[str]
    user_id: int
    account_id: int
    category_id: int
    name: str
    amount: Money
    frequency: Frequency
    start_date: date
    end_date: Optional[date]
    next_payment_date: date
    is_active: bool
    description: Optional[str]
    creation_date: datetime

    @classmethod
    def create_new(
        cls,
        user_id: int,
        account_id: int,
        category_id: int,
        name: str,
        amount: Money,
        frequency: Frequency,
        start_date: date,
        end_date: Optional[date] = None,
        description: Optional[str] = None,
        next_payment_date: Optional[date] = None,
    ):
        if end_date is not None and end_date < start_date:
            raise InvalidIncomeDateRangeError(str(start_date), str(end_date))

        if next_payment_date is None:
            next_payment_date = start_date

        return cls(
            id=None,
            uuid=None,
            user_id=user_id,
            account_id=account_id,
            category_id=category_id,
            name=name,
            amount=amount,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            next_payment_date=next_payment_date,
            is_active=True,
            description=description,
            creation_date=datetime.now(timezone.utc),
        )

    def is_due(self, as_of_date: date) -> bool:
        if not self.is_active:
            return False
        if self.end_date and self.next_payment_date > self.end_date:
            return False
        return self.next_payment_date <= as_of_date

    def advance_next_payment(self) -> None:
        self.next_payment_date = next_occurrence(
            self.next_payment_date, self.frequency, self.start_date.day
        )

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True
