import uuid as uuid_lib
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class APIKey:
    user_id: int
    name: str
    scopes: list[str]
    key_hash: str
    key_prefix: str
    is_active: bool = True
    id: int | None = None
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    uuid: str = field(default_factory=lambda: str(uuid_lib.uuid4()))
    created_at: datetime | None = field(default_factory=lambda: datetime.now(UTC))

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes

    def revoke(self):
        self.is_active = False

    def is_valid(self):
        if not self.is_active:
            return False
        if self.expires_at:
            expires = (
                self.expires_at
                if self.expires_at.tzinfo
                else self.expires_at.replace(tzinfo=UTC)
            )
            if expires < datetime.now(UTC):
                return False
        return True
