from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class AuthAction(StrEnum):
    LOGIN_SUCCEEDED = "login.succeeded"
    LOGIN_FAILED = "login.failed"
    LOGIN_THROTTLED = "login.throttled"
    SESSION_REVOKED = "session.revoked"
    SESSION_REFRESH_REUSE_DETECTED = "session.refresh_reuse_detected"


@dataclass(frozen=True, slots=True)
class AuthEvent:
    """Registro de auditoría de la cuenta y sus sesiones. Nunca lleva contraseñas ni tokens."""

    action: AuthAction
    created_at: datetime
    user_id: int | None = None
    session_id: int | None = None
    ip: str | None = None
    user_agent: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
