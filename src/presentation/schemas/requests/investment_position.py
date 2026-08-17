from decimal import Decimal
from typing import Optional
from datetime import date

from pydantic import Field, BaseModel

from domain.objects.enums import (
    InterestType,
    MaturityAction,
    OverflowAction,
    PositionType,
)


class PositionCapRequest(BaseModel):
    """Tope del apartado y destino del dinero que ya no cabe."""

    max_balance: Optional[Decimal] = Field(
        None,
        gt=Decimal("0"),
        description="Tope de capital. null quita el tope.",
    )
    overflow_action: Optional[OverflowAction] = Field(
        None,
        description=(
            "Qué hacer con el excedente: TO_AVAILABLE (al saldo disponible) "
            "o TO_POSITION (a otro apartado). Por defecto TO_AVAILABLE."
        ),
    )
    overflow_position_uuid: Optional[str] = Field(
        None, description="Apartado destino, obligatorio con TO_POSITION"
    )


class CreatePositionRequest(BaseModel):
    account_uuid: str = Field(..., description="UUID de la cuenta dueña del apartado")
    name: str = Field(..., min_length=1, max_length=100)
    position_type: PositionType = Field(
        ..., description="ON_DEMAND (a la vista) o FIXED_TERM (plazo fijo)"
    )
    amount: Decimal = Field(
        ..., gt=Decimal("0"), description="Monto a apartar del saldo disponible"
    )
    annual_rate: Decimal = Field(..., ge=Decimal("0"), description="Tasa anual (%)")
    interest_type: InterestType = Field(InterestType.COMPOUND)
    term_days: Optional[int] = Field(
        None, ge=1, description="Plazo en días (solo FIXED_TERM)"
    )
    maturity_date: Optional[date] = Field(
        None, description="Fecha de vencimiento (alternativa a term_days)"
    )
    lock_period_end_date: Optional[date] = Field(
        None, description="Fin del periodo de permanencia (no se puede liquidar antes)"
    )
    early_withdrawal_penalty: Optional[Decimal] = Field(
        None,
        ge=Decimal("0"),
        le=Decimal("100"),
        description="Penalización por retiro anticipado (% sobre rendimientos)",
    )
    on_maturity: MaturityAction = Field(
        MaturityAction.HOLD,
        description="Qué hacer al vencer: AUTO_RENEW, LIQUIDATE o HOLD",
    )
    currency: str = Field("MXN", min_length=3, max_length=3)
    cap: Optional[PositionCapRequest] = Field(
        None,
        description=(
            "Tope del apartado (solo a la vista). El monto inicial no puede "
            "superarlo: para eso crea el apartado en el tope y deposita el resto."
        ),
    )


class UpdatePositionRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    cap: Optional[PositionCapRequest] = Field(
        None,
        description=(
            "Configuración de tope. Omítelo para dejarla como está; mándalo "
            "en null para quitar el tope por completo."
        ),
    )


class PositionMovementRequest(BaseModel):
    amount: Decimal = Field(..., gt=Decimal("0"), description="Monto a mover")
    currency: str = Field("MXN", min_length=3, max_length=3)
