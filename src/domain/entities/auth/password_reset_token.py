from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class PasswordResetToken:
    """Enlace de "Olvidé mi contraseña". De un solo uso: `used_at` lo marca canjeado (o
    invalidado porque otro enlace ya cambió la contraseña). Solo se guarda el SHA-256."""

    token_hash: str
    user_id: int
    created_at: datetime
    expires_at: datetime
    used_at: datetime | None = None

    def is_usable(self, now: datetime) -> bool:
        return self.used_at is None and now < self.expires_at
