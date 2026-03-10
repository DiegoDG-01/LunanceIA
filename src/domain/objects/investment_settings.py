from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional
from datetime import date

from domain.objects.enums import InterestType


@dataclass(frozen=True)
class InvestmentCardSettings:
    investment_type: str
    investment_rate: Decimal
    interest_type: InterestType = InterestType.COMPOUND
    lock_period_end_date: Optional[date] = None
    maturity_date: Optional[date] = None
    early_withdrawal_penalty: Optional[Decimal] = None
    base_principal: Optional[Decimal] = None

    def __post_init__(self):
        if self.investment_rate < 0:
            raise ValueError("Interest rate must be non negative")
        if self.early_withdrawal_penalty is not None:
            if not 0 <= self.early_withdrawal_penalty <= 100:
                raise ValueError("Early withdrawal penalty must be between 0 and 100")

        valid_types = ["fixed_term", "stocks", "bonds", "mutual_fund", "etf", "other"]
        if self.investment_type not in valid_types:
            raise ValueError(f"Invalid investment type: {self.investment_type}")
