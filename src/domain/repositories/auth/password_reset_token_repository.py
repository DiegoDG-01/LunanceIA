from abc import ABC, abstractmethod
from datetime import datetime

from domain.entities.auth.password_reset_token import PasswordResetToken


class PasswordResetTokenRepository(ABC):
    @abstractmethod
    async def add(self, token: PasswordResetToken) -> None: ...

    @abstractmethod
    async def get(self, token_hash: str) -> PasswordResetToken | None: ...

    @abstractmethod
    async def consume(self, token_hash: str, now: datetime) -> bool:
        """Marca el token como usado solo si seguía sin usar y vigente. False si otra
        petición lo canjeó antes: de esto depende que cada enlace sirva una sola vez."""

    @abstractmethod
    async def invalidate_for_user(self, user_id: int, now: datetime) -> int:
        """Marca como usados los enlaces pendientes del usuario. Devuelve cuántos."""

    @abstractmethod
    async def purge(self, *, expired_before: datetime, used_before: datetime) -> int:
        """Borra los tokens caducados o usados antes de esas fechas. Devuelve cuántos."""
