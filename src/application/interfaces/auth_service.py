"""Servicios externos que necesitan los casos de uso de autenticación."""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class AccessClaims:
    user_uuid: str
    session_uuid: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class IssuedAccessToken:
    token: str
    expires_in: int


class AccessTokenIssuer(ABC):
    """Firma y verifica el access token (JWT con `sub` = usuario y `sid` = sesión)."""

    @property
    @abstractmethod
    def ttl_seconds(self) -> int: ...

    @abstractmethod
    def issue(self, *, user_uuid: str, session_uuid: str) -> IssuedAccessToken: ...

    @abstractmethod
    def verify(self, token: str) -> AccessClaims:
        """Lanza `JWTValidationError` si el token no es válido o ya caducó."""


class PasswordHasher(ABC):
    @abstractmethod
    async def hash(self, password: str) -> str: ...

    @abstractmethod
    async def verify(self, password: str, password_hash: str) -> bool: ...

    @abstractmethod
    def needs_rehash(self, password_hash: str) -> bool:
        """True si el hash usa otro algoritmo (bcrypt) o parámetros más débiles que los actuales."""

    @abstractmethod
    async def verify_dummy(self, password: str) -> None:
        """Gasta lo mismo que una verificación real: el tiempo de respuesta no revela si el
        usuario existe."""


class SessionRevocationList(ABC):
    """Sesiones cerradas cuyo access token sigue firmado y vigente unos minutos."""

    @abstractmethod
    async def revoke(self, session_uuids: Iterable[str]) -> None: ...

    @abstractmethod
    async def is_revoked(self, session_uuid: str) -> bool: ...


class LoginThrottle(ABC):
    """Bloqueo progresivo de un sujeto (correo + IP, o solo correo) tras varios fallos.

    Si el almacén (Redis) no responde, los métodos lanzan
    `ServiceTemporarilyUnavailableError`: el login no se atiende sin esta protección.
    """

    @abstractmethod
    async def retry_after(self, subject: str) -> int | None:
        """Segundos que quedan de bloqueo, o None si puede intentarlo."""

    @abstractmethod
    async def record_failure(self, subject: str) -> None: ...

    @abstractmethod
    async def reset(self, subject: str) -> None: ...
