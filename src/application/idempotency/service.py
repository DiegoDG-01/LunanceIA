"""Ejecuta una operación de escritura como mucho una vez por `Idempotency-Key`.

Cómo se reparte el trabajo entre transacciones (todas sobre la sesión de BD de la
petición, la misma que usan los repositorios y el `SQLAlchemyUnitOfWork` del handler):

1. `try_claim` inserta la clave sin respuesta. No se confirma todavía.
2. El handler hace su trabajo y su propio `commit()`: la clave y el movimiento de
   dinero quedan confirmados juntos, o ninguno de los dos.
3. Se guarda el código y el cuerpo de la respuesta y se confirma (segunda transacción).

Reintentos con la misma clave:

- Respuesta ya guardada y misma petición: se devuelve esa respuesta sin ejecutar nada.
- Otra petición (método, ruta o cuerpo distinto): `IdempotencyKeyReusedError` (422).
- El handler falló: se hace rollback y la clave desaparece, así que el reintento vuelve
  a ejecutar la operación.
- Petición simultánea: en MySQL/InnoDB el INSERT de la segunda espera al bloqueo de la
  clave primaria que tiene la primera hasta que esta confirma o deshace (sujeto a
  `innodb_lock_wait_timeout`). Si la primera deshizo, el INSERT de la segunda entra y
  ejecuta ella. Si la primera confirmó, la segunda recibe "clave duplicada", hace
  rollback (InnoDB deja un bloqueo compartido sobre la fila duplicada que impediría a
  la primera guardar su respuesta) y relee la fila en una transacción nueva, para ver
  lo último confirmado y no la foto de REPEATABLE READ. Entre el paso 2 y el 3 de la
  primera hay un instante en el que la fila existe sin respuesta: la segunda lo espera
  sondeando hasta `wait_timeout` segundos y después devuelve la misma respuesta.
- Fila sin respuesta pasado `wait_timeout` (el proceso murió entre el paso 2 y el 3):
  `IdempotencyKeyInUseError` (409). El cambio sí se aplicó, así que el cliente debe
  consultar el recurso en lugar de reintentar a ciegas.
"""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from application.interfaces.idempotency import IdempotencyRepository, StoredResponse
from domain.repositories.unit_of_work import AbstractUnitOfWork
from shared.exceptions.application import (
    IdempotencyKeyInUseError,
    IdempotencyKeyReusedError,
)

logger = logging.getLogger(__name__)

# Las claves se guardan al menos este tiempo; el job diario de purga borra las más viejas.
IDEMPOTENCY_TTL = timedelta(hours=24)

# Cuánto espera un reintento a que la petición original guarde su respuesta.
DEFAULT_WAIT_TIMEOUT_SECONDS = 2.0
DEFAULT_POLL_INTERVAL_SECONDS = 0.05


@dataclass(frozen=True, slots=True)
class IdempotentResult:
    response: StoredResponse
    # True si la respuesta viene guardada de una ejecución anterior.
    replayed: bool


class IdempotencyService:
    def __init__(
        self,
        repository: IdempotencyRepository,
        uow: AbstractUnitOfWork,
        *,
        wait_timeout: float = DEFAULT_WAIT_TIMEOUT_SECONDS,
        poll_interval: float = DEFAULT_POLL_INTERVAL_SECONDS,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
    ):
        self.repository = repository
        self.uow = uow
        self.wait_timeout = wait_timeout
        self.poll_interval = poll_interval
        self._now = now
        self._monotonic = monotonic
        self._sleep = sleep

    async def execute(
        self,
        *,
        user_id: int,
        key: str,
        request_hash: str,
        operation: Callable[[], Awaitable[StoredResponse]],
        redact: Callable[[Any], Any] | None = None,
    ) -> IdempotentResult:
        """Ejecuta `operation` si la clave es nueva; si no, devuelve la respuesta guardada.

        `redact` transforma el cuerpo antes de guardarlo (p. ej. para no persistir un
        secreto); la primera respuesta se devuelve completa.
        """
        created_at = self._now()
        stored = await self._claim_or_get_stored(
            user_id=user_id, key=key, request_hash=request_hash, created_at=created_at
        )
        if stored is not None:
            return IdempotentResult(response=stored, replayed=True)

        try:
            response = await operation()
        except BaseException:
            # Deshace la clave reservada (y lo que el handler no confirmó): el
            # reintento vuelve a ejecutar la operación desde cero.
            await self.uow.rollback()
            raise

        to_store = response
        if redact is not None:
            to_store = StoredResponse(
                status_code=response.status_code, body=redact(response.body)
            )
        await self.repository.save_response(
            user_id=user_id,
            key=key,
            request_hash=request_hash,
            response=to_store,
            created_at=created_at,
        )
        await self.uow.commit()
        return IdempotentResult(response=response, replayed=False)

    async def _claim_or_get_stored(
        self, *, user_id: int, key: str, request_hash: str, created_at: datetime
    ) -> StoredResponse | None:
        """Reserva la clave (devuelve None) o devuelve la respuesta ya guardada."""
        deadline = self._monotonic() + self.wait_timeout
        while True:
            if await self.repository.try_claim(
                user_id=user_id,
                key=key,
                request_hash=request_hash,
                created_at=created_at,
            ):
                return None

            # Clave duplicada: soltar el bloqueo compartido de InnoDB y leer lo
            # último confirmado en una transacción nueva.
            await self.uow.rollback()
            record = await self.repository.get(user_id=user_id, key=key)
            await self.uow.rollback()

            if record is not None:
                if record.request_hash != request_hash:
                    raise IdempotencyKeyReusedError()
                if record.response is not None:
                    return record.response
            # Sin fila (la original se deshizo o se purgó) se reintenta reservar;
            # con fila sin respuesta se espera a que la original la guarde.
            if self._monotonic() >= deadline:
                logger.warning(
                    "Idempotency-Key sin respuesta guardada tras %.1fs (user_id=%s)",
                    self.wait_timeout,
                    user_id,
                )
                raise IdempotencyKeyInUseError()
            await self._sleep(self.poll_interval)
