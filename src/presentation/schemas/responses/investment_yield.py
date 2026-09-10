from datetime import date, datetime
from decimal import Decimal

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
    created_at: datetime | None


class ProjectionDayResponse(BaseModel):
    projection_date: date
    principal_amount: Decimal
    yield_amount: Decimal
    projected_balance: Decimal
    overflow_amount: Decimal = Decimal(0)


class InvestmentProjectionResponse(BaseModel):
    account_uuid: str
    current_balance: Decimal
    # Solo se llenan cuando la cuenta tiene un único apartado activo
    annual_rate: Decimal | None
    interest_type: InterestType | None
    maturity_date: date | None
    projected_final_balance: Decimal | None
    daily_projections: list[ProjectionDayResponse]
