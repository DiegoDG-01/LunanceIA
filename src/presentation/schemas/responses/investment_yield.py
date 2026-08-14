from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel

from domain.objects.enums import InterestType


class InvestmentYieldResponse(BaseModel):
    uuid: str
    yield_date: date
    principal_amount: Decimal
    yield_amount: Decimal
    cumulative_balance: Decimal
    annual_rate: Decimal
    interest_type: InterestType
    created_at: Optional[datetime]


class ProjectionDayResponse(BaseModel):
    projection_date: date
    principal_amount: Decimal
    yield_amount: Decimal
    projected_balance: Decimal


class InvestmentProjectionResponse(BaseModel):
    account_uuid: str
    current_balance: Decimal
    # Solo se llenan cuando la cuenta tiene un único apartado activo
    annual_rate: Optional[Decimal]
    interest_type: Optional[InterestType]
    maturity_date: Optional[date]
    projected_final_balance: Optional[Decimal]
    daily_projections: List[ProjectionDayResponse]
