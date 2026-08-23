from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List

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
    term_days: Optional[int] = None
    lock_period_end_date: Optional[date] = None
    maturity_date: Optional[date] = None
    early_withdrawal_penalty: Optional[Decimal] = None
    max_balance: Optional[Decimal] = None
    overflow_action: Optional[OverflowAction] = None
    overflow_position_uuid: Optional[str] = None
    created_at: Optional[datetime] = None
    account_available_balance: Optional[Decimal] = None


class AccountPositionsResponse(BaseModel):
    account_uuid: str
    account_name: str
    available_balance: Decimal
    invested_balance: Decimal
    total_balance: Decimal
    currency: str
    positions: List[PositionResponse]


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
    maturity_date: Optional[date]
    projected_final_balance: Decimal
    daily_projections: List[ProjectionDayResponse]
    projected_overflow: Decimal = Decimal(0)
    max_balance: Optional[Decimal] = None
