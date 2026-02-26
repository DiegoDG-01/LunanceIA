from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List

from domain.objects.enums import InterestType


@dataclass
class InvestmentYieldResponseDTO:
    uuid: str
    yield_date: date
    principal_amount: Decimal
    yield_amount: Decimal
    cumulative_balance: Decimal
    annual_rate: Decimal
    interest_type: InterestType
    created_at: Optional[datetime]


    @classmethod
    def from_entity(cls, entity) -> 'InvestmentYieldResponseDTO':
        return cls(
            uuid=entity.uuid,
            yield_date=entity.yield_date,
            principal_amount=entity.principal_amount,
            yield_amount=entity.yield_amount,
            cumulative_balance=entity.cumulative_balance,
            annual_rate=entity.annual_rate,
            interest_type=entity.interest_type,
            created_at=entity.created_at
        )


@dataclass
class ProjectionDayDTO:
    projection_date: date
    principal_amount: Decimal
    yield_amount: Decimal
    projected_balance: Decimal


@dataclass
class InvestmentProjectionResponseDTO:
    account_uuid: str
    current_balance: Decimal
    annual_rate: Decimal
    interest_type: InterestType
    maturity_date: Optional[date]
    projected_final_balance: Optional[Decimal]
    daily_projections: List[ProjectionDayDTO]
