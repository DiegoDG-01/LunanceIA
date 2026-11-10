from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AuthConfig:
    access_token_expire_minutes: int
    refresh_token_expire_days: int


class AuthTokenServiceInterface(ABC):
    @abstractmethod
    def check_password(self, plain_password: str, hashed_password: str) -> bool: ...

    @abstractmethod
    def create_access_token(
        self, user_uuid: str, expires_in: int | None = None
    ) -> str: ...

    @abstractmethod
    def create_refresh_token(
        self, user_uuid: str, expires_in: int | None = None
    ) -> str: ...

    @abstractmethod
    async def verify_refresh_token(self, token: str) -> str | None: ...

    @abstractmethod
    def get_password_hash(self, password: str) -> str: ...

    @abstractmethod
    def hash_refresh_token(self, token: str) -> str: ...


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
