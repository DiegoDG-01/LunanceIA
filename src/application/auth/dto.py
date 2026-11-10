from dataclasses import dataclass

from domain.entities.auth.session import Platform, UserSession


@dataclass(frozen=True, slots=True)
class ClientContext:
    """Quién hace la petición: dispositivo (`X-Lunance-Device`), app (`X-Lunance-Client`),
    IP y user agent."""

    device_id: str | None = None
    platform: Platform = Platform.WEB
    client: str | None = None
    ip: str | None = None
    user_agent: str | None = None
    device_name: str | None = None


@dataclass(frozen=True, slots=True)
class IssuedSession:
    session: UserSession
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"
