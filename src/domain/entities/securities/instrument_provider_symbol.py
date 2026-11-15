from dataclasses import dataclass
from datetime import datetime

from domain.objects.enums import ProviderSymbolStatus


@dataclass
class InstrumentProviderSymbol:
    """Cómo llama un proveedor a un valor y si lo tiene."""

    instrument_id: int
    provider: str
    provider_symbol: str
    status: ProviderSymbolStatus = ProviderSymbolStatus.ACTIVE
    checked_at: datetime | None = None
