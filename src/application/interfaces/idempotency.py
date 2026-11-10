"""Contrato de almacenamiento de `Idempotency-Key` (ver `IdempotencyService`)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class StoredResponse:
    """Respuesta HTTP serializada: lo que se devuelve tal cual en un reintento."""

    status_code: int
    # JSON ya serializable (dict, list, str, ...); None si la respuesta no tiene cuerpo.
    body: Any


@dataclass(frozen=True, slots=True)
class IdempotencyRecord:
    """Fila de `idempotency_keys`. `response` es None mientras no se haya guardado."""

    request_hash: str
    response: StoredResponse | None


class IdempotencyRepository(ABC):
    """Persistencia de claves. Las claves son por usuario: `(user_id, key)` es único."""

    @abstractmethod
    async def try_claim(
        self, *, user_id: int, key: str, request_hash: str, created_at: datetime
    ) -> bool:
        """Inserta la clave "en curso" (sin respuesta) en la transacción actual.

        Devuelve False si la clave ya existe. No confirma: la fila se guarda con el
        commit del handler, junto con el cambio que protege.
        """

    @abstractmethod
    async def get(self, *, user_id: int, key: str) -> IdempotencyRecord | None:
        """Lee la clave tal como está confirmada en la base de datos."""

    @abstractmethod
    async def save_response(
        self,
        *,
        user_id: int,
        key: str,
        request_hash: str,
        response: StoredResponse,
        created_at: datetime,
    ) -> None:
        """Guarda la respuesta de una clave reservada (no confirma)."""

    @abstractmethod
    async def purge(self, *, created_before: datetime) -> int:
        """Borra las claves creadas antes de `created_before`. Devuelve cuántas borró."""
