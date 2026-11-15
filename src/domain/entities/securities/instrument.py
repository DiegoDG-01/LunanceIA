from dataclasses import dataclass
from datetime import date, datetime

from domain.objects.enums import InstrumentType, Market


@dataclass
class Instrument:
    """Un valor que cotiza en bolsa: acción, ETF o FIBRA. El catálogo es global (no es de un
    usuario); los precios solo se descargan de los valores con `tracked_since`."""

    id: int | None
    uuid: str | None
    market: Market
    # BMV y SIC: emisora + serie (`WALMEX*`, `FUNO11`, `AAPL*`); US: ticker (`AAPL`).
    symbol: str
    name: str
    instrument_type: InstrumentType
    currency: str
    isin: str | None = None
    exchange: str | None = None
    # Proveedor fijo del valor: el primero que respondió. Los demás solo cubren sus fallas.
    preferred_provider: str | None = None
    is_active: bool = True
    # Desde qué día se guardan precios. None: nadie lo usa y el job lo salta.
    tracked_since: date | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def track_from(self, since: date) -> bool:
        """Empieza (o adelanta hacia atrás) el seguimiento. True si cambió."""
        if self.tracked_since is not None and self.tracked_since <= since:
            return False
        self.tracked_since = since
        return True
