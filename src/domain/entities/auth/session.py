import uuid as uuid_lib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum


class Platform(StrEnum):
    WEB = "web"
    IOS = "ios"
    ANDROID = "android"

    @property
    def is_mobile(self) -> bool:
        return self is not Platform.WEB


class RevocationReason(StrEnum):
    SIGNED_OUT = "signed_out"
    SIGNED_OUT_EVERYWHERE = "signed_out_everywhere"
    REPLACED = "replaced"
    REVOKED_BY_USER = "revoked_by_user"
    REFRESH_REUSE = "refresh_reuse"
    PASSWORD_RESET = "password_reset"
    PASSWORD_CHANGE = "password_change"
    # Aviso de Apple: el usuario dejó de usar su Apple ID con Lunance o lo borró.
    APPLE_REVOKED = "apple_revoked"


@dataclass(frozen=True, slots=True)
class SessionLifetime:
    """Cuánto vive una sesión sin usarse (`idle`) y cuánto como máximo desde el login."""

    idle: timedelta
    absolute: timedelta


@dataclass(slots=True)
class UserSession:
    """Una sesión por dispositivo (`X-Lunance-Device`). Su `uuid` es el `sid` del access token."""

    user_id: int
    device_id: str
    platform: Platform
    created_at: datetime
    last_seen_at: datetime
    idle_expires_at: datetime
    absolute_expires_at: datetime
    created_ip: str | None = None
    last_ip: str | None = None
    device_name: str | None = None
    client: str | None = None
    user_agent: str | None = None
    revoked_at: datetime | None = None
    revoked_reason: RevocationReason | None = None
    id: int | None = None
    uuid: str = field(default_factory=lambda: str(uuid_lib.uuid4()))

    @classmethod
    def open(
        cls,
        *,
        user_id: int,
        device_id: str,
        platform: Platform,
        lifetime: SessionLifetime,
        now: datetime,
        ip: str | None = None,
        device_name: str | None = None,
        client: str | None = None,
        user_agent: str | None = None,
    ) -> "UserSession":
        absolute = now + lifetime.absolute
        return cls(
            user_id=user_id,
            device_id=device_id,
            platform=platform,
            created_at=now,
            last_seen_at=now,
            idle_expires_at=min(now + lifetime.idle, absolute),
            absolute_expires_at=absolute,
            created_ip=ip,
            last_ip=ip,
            device_name=device_name,
            client=client,
            user_agent=user_agent,
        )

    @property
    def expires_at(self) -> datetime:
        return min(self.idle_expires_at, self.absolute_expires_at)

    def is_active(self, now: datetime) -> bool:
        return self.revoked_at is None and now < self.expires_at

    def revoke(self, now: datetime, reason: RevocationReason) -> None:
        if self.revoked_at is None:
            self.revoked_at = now
            self.revoked_reason = reason

    def touch(self, now: datetime, idle: timedelta, ip: str | None = None) -> None:
        """Cada refresh renueva la inactividad, pero nunca pasa del máximo absoluto."""
        self.last_seen_at = now
        self.idle_expires_at = min(now + idle, self.absolute_expires_at)
        if ip:
            self.last_ip = ip
