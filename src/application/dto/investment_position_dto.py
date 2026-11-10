from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from domain.objects.enums import (
    InterestType,
    MaturityAction,
    OverflowAction,
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
    term_days: int | None = None
    maturity_date: date | None = None
    lock_period_end_date: date | None = None
    early_withdrawal_penalty: Decimal | None = None
    on_maturity: MaturityAction = MaturityAction.HOLD
    currency: str = "MXN"
    max_balance: Decimal | None = None
    overflow_action: OverflowAction | None = None
    overflow_position_uuid: str | None = None


@dataclass
class PositionMovementDTO:
    """DTO para depositar o retirar dinero de un apartado."""

    user_id: int
    position_uuid: str
    amount: Decimal
    currency: str = "MXN"


@dataclass
class UpdatePositionDTO:
    """DTO para actualizar el nombre y la configuración de tope de un apartado.

    `cap_provided` distingue "no mandaron la configuración de tope" de
    "mandaron quitarla": sin esa bandera, un PATCH que solo cambia el nombre
    borraría el tope sin querer.
    """

    user_id: int
    position_uuid: str
    name: str | None = None
    cap_provided: bool = False
    max_balance: Decimal | None = None
    overflow_action: OverflowAction | None = None
    overflow_position_uuid: str | None = None


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
    term_days: int | None = None
    lock_period_end_date: date | None = None
    maturity_date: date | None = None
    early_withdrawal_penalty: Decimal | None = None
    max_balance: Decimal | None = None
    overflow_action: OverflowAction | None = None
    overflow_position_uuid: str | None = None
    created_at: datetime | None = None
    account_available_balance: Decimal | None = None

    @classmethod
    def from_entity(
        cls,
        position,
        account_uuid: str,
        account_available_balance: Decimal | None = None,
        overflow_position_uuid: str | None = None,
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
            max_balance=position.max_balance,
            overflow_action=position.overflow_action,
            overflow_position_uuid=overflow_position_uuid,
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
    maturity_date: date | None
    projected_final_balance: Decimal
    daily_projections: list
    # Total que se desborda en el horizonte proyectado (0 si no hay tope)
    projected_overflow: Decimal = Decimal(0)
    max_balance: Decimal | None = None
