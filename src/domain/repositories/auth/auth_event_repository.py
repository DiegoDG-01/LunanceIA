from abc import ABC, abstractmethod
from datetime import datetime

from domain.entities.auth.auth_event import AuthEvent


class AuthEventRepository(ABC):
    @abstractmethod
    async def record(self, event: AuthEvent) -> None:
        """Añade un evento a la transacción en curso."""

    @abstractmethod
    async def purge(self, *, created_before: datetime) -> int:
        """Borra los eventos anteriores a `created_before`. Devuelve cuántos borró."""
