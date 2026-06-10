from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional
import uuid as uuid_lib


@dataclass
class APIKey:
    user_id: int
    name: str
    scopes: list[str]
    key_hash: str
    key_prefix: str
    is_active: bool = True
    id: Optional[int] = None
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    uuid: str = field(
        default_factory=lambda: str(uuid_lib.uuid4())
    )
    created_at: Optional[datetime] = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes

    def revoke(self):
        self.is_active = False

    def is_valid(self):
        if not self.is_active:
            return False
        if self.expires_at:
            expires = self.expires_at if self.expires_at.tzinfo else self.expires_at.replace(tzinfo=timezone.utc)
            if expires < datetime.now(timezone.utc):
                return False
        return True






