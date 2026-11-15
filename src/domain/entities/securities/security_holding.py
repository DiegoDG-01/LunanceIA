from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from domain.objects.enums import HoldingStatus


@dataclass
class SecurityHolding:
    """Lo que hay de un valor en una cuenta. Se calcula de las operaciones: es una caché, no
    la fuente de verdad."""

    id: int | None
    uuid: str | None
    user_id: int
    account_id: int
    instrument_id: int
    quantity: Decimal
    # Costo promedio por título (incluye comisiones de compra) y costo total de lo que hay.
    avg_cost: Decimal
    cost_basis: Decimal
    realized_pnl: Decimal
    dividends: Decimal
    status: HoldingStatus
    opened_at: date | None = None
    closed_at: date | None = None
    updated_at: datetime | None = None
