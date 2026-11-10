from abc import ABC, abstractmethod
from datetime import datetime

from domain.entities.auth.refresh_token import RefreshToken


class RefreshTokenRepository(ABC):
    @abstractmethod
    async def add(self, token: RefreshToken) -> None:
        """Guarda el hash de un refresh token recién emitido."""

    @abstractmethod
    async def get(
        self, token_hash: str, *, for_update: bool = False
    ) -> RefreshToken | None:
        """Token por su hash. `for_update` lee la última versión confirmada y la bloquea."""

    @abstractmethod
    async def rotate_active(self, session_id: int, now: datetime) -> None:
        """Marca como canjeados todos los tokens vigentes de la sesión."""
