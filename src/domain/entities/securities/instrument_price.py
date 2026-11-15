from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass
class InstrumentPrice:
    """Cierre de un día, sin ajustar, en la moneda del valor."""

    instrument_id: int
    price_date: date
    close: Decimal
    provider: str
    traded_value: Decimal | None = None
    # False en feriados que el proveedor rellena con el cierre anterior.
    is_trading_day: bool = True
    fetched_at: datetime | None = None
