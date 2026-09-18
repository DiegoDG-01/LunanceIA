from dataclasses import dataclass
from datetime import datetime


@dataclass
class RefreshToken:
    user_id: int
    token_hash: str
    is_revoked: bool
    expired_at: datetime
    id: int | None = None
    created_at: datetime | None = None
