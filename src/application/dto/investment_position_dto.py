from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from datetime import date, datetime

from domain.objects.enums import (
    InterestType,
    MaturityAction,
    PositionStatus,
    PositionType,
)


@dataclass
class CreatePositionDTO:
    """DTO para crear un apartado de inversión."""

    user_id: int
    account_uuid: str
    name: str
    position_type: PositionType
    amount: Decimal
    annual_rate: Decimal
    interest_type: InterestType = InterestType.COMPOUND
    term_days: Optional[int] = None
    maturity_date: Optional[date] = None
    lock_period_end_date: Optional[date] = None
    early_withdrawal_penalty: Optional[Decimal] = None
    on_maturity: MaturityAction = MaturityAction.HOLD
    currency: str = "MXN"


@dataclass
class PositionMovementDTO:
    """DTO para depositar o retirar dinero de un apartado."""

    user_id: int
    position_uuid: str
    amount: Decimal
    currency: str = "MXN"


@dataclass
class LiquidatePositionDTO:
    """DTO para liquidar un apartado por completo."""

    user_id: int
    position_uuid: str


@dataclass
class PositionResponseDTO:
    """DTO de respuesta de un apartado de inversión."""

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
    created_at: Optional[datetime] = None
    account_available_balance: Optional[Decimal] = None

    @classmethod
    def from_entity(
        cls,
        position,
        account_uuid: str,
        account_available_balance: Optional[Decimal] = None,
    ) -> "PositionResponseDTO":
        return cls(
            position_uuid=position.uuid,
            account_uuid=account_uuid,
            name=position.name,
            position_type=position.position_type,
            status=position.status,
            balance=position.balance.amount,
            accrued_yield=position.accrued_yield.amount,
            total_value=position.total_value.amount,
            currency=position.balance.currency,
            annual_rate=position.annual_rate,
            interest_type=position.interest_type,
            start_date=position.start_date,
            on_maturity=position.on_maturity,
            term_days=position.term_days,
            lock_period_end_date=position.lock_period_end_date,
            maturity_date=position.maturity_date,
            early_withdrawal_penalty=position.early_withdrawal_penalty,
            created_at=position.created_at,
            account_available_balance=account_available_balance,
        )


@dataclass
class LiquidatePositionResponseDTO:
    """DTO de respuesta al liquidar un apartado."""

    position_uuid: str
    name: str
    payout_amount: Decimal
    currency: str
    status: PositionStatus
    account_uuid: str
    account_available_balance: Decimal


@dataclass
class AccountPositionsResponseDTO:
    """DTO de respuesta con los apartados de una cuenta y sus totales."""

    account_uuid: str
    account_name: str
    available_balance: Decimal
    invested_balance: Decimal
    total_balance: Decimal
    currency: str
    positions: list[PositionResponseDTO]


@dataclass
class PositionProjectionResponseDTO:
    """DTO de respuesta de proyección de un apartado."""

    position_uuid: str
    name: str
    current_value: Decimal
    annual_rate: Decimal
    interest_type: InterestType
    maturity_date: Optional[date]
    projected_final_balance: Decimal
    daily_projections: list
