from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class RefreshToken:
    """Solo se guarda el SHA-256 del token. `rotated_at` marca que ya se canjeó por su sucesor."""

    token_hash: str
    session_id: int
    created_at: datetime
    rotated_at: datetime | None = None
