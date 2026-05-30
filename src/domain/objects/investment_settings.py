from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from datetime import date

from domain.objects.enums import InterestType
from shared.exceptions.domain import (
    InvalidInvestmentRateError,
    InvalidPenaltyPercentageError,
    InvalidInvestmentTypeError,
)


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
            raise InvalidInvestmentRateError(str(self.investment_rate))
        if self.early_withdrawal_penalty is not None:
            if not 0 <= self.early_withdrawal_penalty <= 100:
                raise InvalidPenaltyPercentageError(str(self.early_withdrawal_penalty))

        valid_types = [
            "fixed_term",
            "stocks",
            "bonds",
            "mutual_fund",
            "etf",
            "other",
            "variable",
        ]
        if self.investment_type not in valid_types:
            raise InvalidInvestmentTypeError(self.investment_type)
