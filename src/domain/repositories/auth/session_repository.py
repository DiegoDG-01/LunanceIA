from abc import ABC, abstractmethod
from datetime import datetime

from domain.entities.auth.session import RevocationReason, UserSession


class SessionRepository(ABC):
    @abstractmethod
    async def add(self, session: UserSession) -> UserSession:
        """Guarda una sesión nueva y devuelve la entidad con su `id`."""

    @abstractmethod
    async def get(
        self, session_id: int, *, for_update: bool = False
    ) -> UserSession | None:
        """Sesión por id interno. `for_update` la bloquea hasta el fin de la transacción."""

    @abstractmethod
    async def get_by_uuid(
        self, session_uuid: str, *, for_update: bool = False
    ) -> UserSession | None:
        """Sesión por su uuid público (el `sid` del access token)."""

    @abstractmethod
    async def save(self, session: UserSession) -> None:
        """Persiste los cambios de una sesión existente."""

    @abstractmethod
    async def list_active(self, user_id: int, now: datetime) -> list[UserSession]:
        """Sesiones no revocadas ni vencidas del usuario, la usada más recientemente primero."""

    @abstractmethod
    async def revoke_active(
        self,
        user_id: int,
        now: datetime,
        reason: RevocationReason,
        *,
        device_id: str | None = None,
        except_uuid: str | None = None,
    ) -> list[UserSession]:
        """Revoca las sesiones abiertas del usuario (o solo las de un dispositivo) y las devuelve.

        `except_uuid` conserva esa sesión (cambiar la contraseña no cierra la actual)."""

    @abstractmethod
    async def has_device(self, user_id: int, device_id: str) -> bool:
        """True si el dispositivo tuvo alguna vez sesión en la cuenta (aunque ya esté cerrada
        y mientras no se purgue)."""

    @abstractmethod
    async def purge(self, *, expired_before: datetime, revoked_before: datetime) -> int:
        """Borra las sesiones vencidas antes de `expired_before` o revocadas antes de
        `revoked_before` (sus refresh tokens se van en cascada). Devuelve cuántas borró."""
