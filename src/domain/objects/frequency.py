from domain.objects.enums import Frequency
from dateutil.relativedelta import relativedelta

from datetime import date
from typing import Optional

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


def next_occurrence(current: date, frequency: Frequency, anchor_day: int) -> date:
    advance = current + _FREQUENCY_DELTAS[frequency]
    if frequency in _MONTH_BASED:
        advance = advance.replace(
            day=min(anchor_day, days_in_month(advance.year, advance.month))
        )
    return advance


def first_occurrence(
    start_date: date,
    frequency: Frequency,
    anchor_day: Optional[int] = None,
) -> date:
    if frequency not in _MONTH_BASED or anchor_day is None:
        return start_date

    clamped = min(anchor_day, days_in_month(start_date.year, start_date.month))
    candidate = start_date.replace(day=clamped)
    if candidate < start_date:
        candidate = next_occurrence(candidate, frequency, anchor_day)
    return candidate
