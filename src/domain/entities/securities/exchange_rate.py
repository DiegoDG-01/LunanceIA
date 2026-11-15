from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass
class ExchangeRate:
    """Unidades de `quote` por una de `base` (USD/MXN: pesos por dólar, FIX de Banxico)."""

    base: str
    quote: str
    rate_date: date
    rate: Decimal
    provider: str
    fetched_at: datetime | None = None
