from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class CreditCardSettings:
    billing_cycle_day: int
    payment_due_day: int
    credit_limit: Optional[Decimal] = None
    minimum_payment_percentage: Optional[Decimal] = None

    def __post_init__(self):
        if not 1 <= self.billing_cycle_day <= 31:
            raise ValueError("Billing cycle days must be between 1 and 31")
        if not 1 <= self.payment_due_day <= 31:
            raise ValueError("Payment due days must be between 1 and 31")
        if self.credit_limit is not None and self.credit_limit <= 0:
            raise ValueError("Credit limit must be non negative")
        if self.minimum_payment_percentage is not None:
            if not 0 <= self.minimum_payment_percentage <= 100:
                raise ValueError("Minimum payment percentage must be between 0 and 100")
