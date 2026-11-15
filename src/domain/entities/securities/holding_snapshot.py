from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass
class HoldingSnapshot:
    """Cómo estaba una tenencia al final de un día de calendario.

    Los días sin cierre (fines de semana, feriados, proveedor caído) usan el último cierre
    conocido: `price_date` dice de qué día es. Sin ningún cierre todavía, la valuación queda
    en None. `market_value_mxn` usa el FIX del día (o el último publicado) si el valor no es
    en pesos.
    """

    holding_id: int
    snapshot_date: date
    quantity: Decimal
    cost_basis: Decimal
    realized_pnl: Decimal
    dividends: Decimal
    close: Decimal | None = None
    price_date: date | None = None
    fx_rate: Decimal | None = None
    market_value: Decimal | None = None
    market_value_mxn: Decimal | None = None
    unrealized_pnl: Decimal | None = None
