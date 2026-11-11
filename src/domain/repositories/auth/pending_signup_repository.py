from abc import ABC, abstractmethod
from datetime import datetime

from domain.entities.auth.pending_signup import EmailVerificationToken, PendingSignup


class PendingSignupRepository(ABC):
    @abstractmethod
    async def get_by_email(
        self, email: str, *, for_update: bool = False
    ) -> PendingSignup | None:
        """Registro (abierto o caducado) del correo ya normalizado."""

    @abstractmethod
    async def get_by_username(self, username: str) -> PendingSignup | None:
        """Registro (abierto o caducado) que reserva el username."""

    @abstractmethod
    async def get(
        self, signup_id: int, *, for_update: bool = False
    ) -> PendingSignup | None: ...

    @abstractmethod
    async def add(self, signup: PendingSignup) -> PendingSignup:
        """Guarda un registro nuevo y lo devuelve con su `id`. Lanza `IntegrityError` si el
        correo o el username ya están en otro registro."""

    @abstractmethod
    async def save(self, signup: PendingSignup) -> None:
        """Persiste los cambios de un registro existente."""

    @abstractmethod
    async def delete(self, signup_id: int) -> None:
        """Borra el registro y todos sus enlaces."""

    @abstractmethod
    async def add_token(self, token: EmailVerificationToken) -> None: ...

    @abstractmethod
    async def get_token(self, token_hash: str) -> EmailVerificationToken | None: ...

    @abstractmethod
    async def delete_tokens(self, signup_id: int) -> None:
        """Invalida todos los enlaces enviados para el registro."""

    @abstractmethod
    async def purge(self, *, expired_before: datetime) -> int:
        """Borra los registros caducados antes de `expired_before` (con sus enlaces).
        Devuelve cuántos registros borró."""
