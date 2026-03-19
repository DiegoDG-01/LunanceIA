from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from shared.exceptions.domain import (
    InvalidBillingCycleDayError,
    InvalidPaymentDueDayError,
    InvalidCreditLimitError,
    InvalidMinimumPaymentError,
)


@dataclass(frozen=True)
class CreditCardSettings:
    billing_cycle_day: int
    payment_due_day: int
    credit_limit: Optional[Decimal] = None
    minimum_payment_percentage: Optional[Decimal] = None

    def __post_init__(self):
        if not 1 <= self.billing_cycle_day <= 31:
            raise InvalidBillingCycleDayError(str(self.billing_cycle_day))
        if not 1 <= self.payment_due_day <= 31:
            raise InvalidPaymentDueDayError("Payment due days must be between 1 and 31")
        if self.credit_limit is not None and self.credit_limit <= 0:
            raise InvalidCreditLimitError(str(self.credit_limit))
        if self.minimum_payment_percentage is not None:
            if not 0 <= self.minimum_payment_percentage <= 100:
                raise InvalidMinimumPaymentError(str(self.minimum_payment_percentage))
