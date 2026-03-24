from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class RefreshToken:
    user_id: int
    token_hash: str
    is_revoked: bool
    expired_at: datetime
    id: Optional[int] = None
    created_at: Optional[datetime] = None
