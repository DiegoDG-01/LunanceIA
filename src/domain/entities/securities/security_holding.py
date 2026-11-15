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
    # Fotos diarias: hasta qué día están hechas y desde qué día hay que rehacerlas (una
    # operación, un precio o un tipo de cambio cambió). None: no hay nada pendiente.
    snapshots_through: date | None = None
    snapshots_dirty_from: date | None = None

    def mark_dirty_from(self, day: date) -> None:
        if self.snapshots_dirty_from is None or day < self.snapshots_dirty_from:
            self.snapshots_dirty_from = day
