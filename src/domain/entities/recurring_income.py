from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional

from dateutil.relativedelta import relativedelta

from domain.objects.enums import Frequency
from domain.objects.money import Money
from shared.exceptions.domain import InvalidIncomeDateRangeError
from shared.utils.date import days_in_month

_FREQUENCY_DELTAS = {
    Frequency.DAILY: relativedelta(days=1),
    Frequency.WEEKLY: relativedelta(weeks=1),
    Frequency.BIWEEKLY: relativedelta(weeks=2),
    Frequency.MONTHLY: relativedelta(months=1),
    Frequency.BIMONTHLY: relativedelta(months=2),
    Frequency.QUARTERLY: relativedelta(months=3),
    Frequency.SEMI_ANNUAL: relativedelta(months=6),
    Frequency.ANNUAL: relativedelta(years=1),
}
_MONTH_BASED = {
    Frequency.MONTHLY,
    Frequency.BIMONTHLY,
    Frequency.QUARTERLY,
    Frequency.SEMI_ANNUAL,
    Frequency.ANNUAL,
}


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
        advanced = self.next_payment_date + _FREQUENCY_DELTAS[self.frequency]
        if self.frequency in _MONTH_BASED:
            day = min(self.start_date.day, days_in_month(advanced.year, advanced.month))
            advanced = advanced.replace(day=day)
        self.next_payment_date = advanced

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True
