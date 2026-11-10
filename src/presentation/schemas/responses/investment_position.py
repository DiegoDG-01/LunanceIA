from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from domain.objects.enums import (
    InterestType,
    MaturityAction,
    OverflowAction,
    PositionStatus,
    PositionType,
)
from presentation.schemas.responses.investment_yield import ProjectionDayResponse


class PositionResponse(BaseModel):
    position_uuid: str
    account_uuid: str
    name: str
    position_type: PositionType
    status: PositionStatus
    balance: Decimal
    accrued_yield: Decimal
    total_value: Decimal
    currency: str
    annual_rate: Decimal
    interest_type: InterestType
    start_date: date
    on_maturity: MaturityAction
    term_days: int | None = None
    lock_period_end_date: date | None = None
    maturity_date: date | None = None
    early_withdrawal_penalty: Decimal | None = None
    max_balance: Decimal | None = None
    overflow_action: OverflowAction | None = None
    overflow_position_uuid: str | None = None
    created_at: datetime | None = None
    account_available_balance: Decimal | None = None


class AccountPositionsResponse(BaseModel):
    account_uuid: str
    account_name: str
    available_balance: Decimal
    invested_balance: Decimal
    total_balance: Decimal
    currency: str
    positions: list[PositionResponse]


class LiquidatePositionResponse(BaseModel):
    position_uuid: str
    name: str
    payout_amount: Decimal
    currency: str
    status: PositionStatus
    account_uuid: str
    account_available_balance: Decimal


class PositionProjectionResponse(BaseModel):
    position_uuid: str
    name: str
    current_value: Decimal
    annual_rate: Decimal
    interest_type: InterestType
    maturity_date: date | None
    projected_final_balance: Decimal
    daily_projections: list[ProjectionDayResponse]
    projected_overflow: Decimal = Decimal(0)
    max_balance: Decimal | None = None
