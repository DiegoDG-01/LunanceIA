"""Header `Idempotency-Key`: un reintento de la app nunca repite un movimiento de dinero.

Uso en un endpoint (la llamada al handler va dentro de `operation`):

    idempotency: Idempotency = Depends(require_idempotency_key)  # POST que crea
    idempotency: Idempotency = Depends(accept_idempotency_key)   # PUT/PATCH/DELETE

    async def operation():
        result = await handler.handle(command)
        return SomeResponse(**result.__dict__)

    return await idempotency.run(cast(int, current_user.id), operation)

La reserva de la clave, el handler y el guardado de la respuesta usan la sesión de BD
de la petición (`get_db` se cachea por petición), así que el `commit()` del handler
confirma la clave y el cambio juntos. El flujo completo está en `IdempotencyService`.
"""

import hashlib
import json
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from fastapi import Depends, Header, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from application.idempotency.service import IdempotencyService, IdempotentResult
from application.interfaces.idempotency import IdempotencyRepository, StoredResponse
from domain.repositories.unit_of_work import AbstractUnitOfWork
from presentation.dependencies.repositories import (
    get_idempotency_repository,
    get_unit_of_work_repository,
)

IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"
# Se añade a las respuestas devueltas desde la tabla, sin ejecutar el handler.
IDEMPOTENT_REPLAYED_HEADER = "Idempotent-Replayed"

_HEADER_DESCRIPTION = (
    "UUID generado por el cliente para esta operación. Si la respuesta no llega, "
    "reintenta con la misma clave y el mismo cuerpo: recibirás la respuesta original "
    "sin que la operación se repita."
)


class Idempotency:
    """Protección de una petición concreta. Sin clave, `run` solo ejecuta la operación."""

    def __init__(
        self,
        request: Request,
        service: IdempotencyService,
        key: str | None,
        request_hash: str | None,
    ):
        self._request = request
        self.service = service
        self.key = key
        self.request_hash = request_hash

    async def run(
        self,
        user_id: int,
        operation: Callable[[], Awaitable[Any]],
        *,
        redact: Callable[[Any], Any] | None = None,
    ) -> Any:
        """Ejecuta `operation` (que llama al handler) como mucho una vez por clave.

        `operation` devuelve lo mismo que devolvería el endpoint: un modelo de
        respuesta, un `Response` o None. `redact` cambia el cuerpo que se guarda para
        los reintentos (no el de esta respuesta).
        """
        if self.key is None or self.request_hash is None:
            return await operation()

        async def execute() -> StoredResponse:
            return self._to_stored(await operation())

        result = await self.service.execute(
            user_id=user_id,
            key=self.key,
            request_hash=self.request_hash,
            operation=execute,
            redact=redact,
        )
        return _to_http_response(result)

    def _to_stored(self, result: Any) -> StoredResponse:
        if isinstance(result, Response):
            if result.body and not isinstance(result, JSONResponse):
                raise TypeError("Solo se pueden guardar respuestas JSON o sin cuerpo")
            body = json.loads(bytes(result.body)) if result.body else None
            return StoredResponse(status_code=result.status_code, body=body)
        # El mismo código que FastAPI usaría para este endpoint (`status_code=` del
        # decorador, 200 si no se declaró).
        route = self._request.scope.get("route")
        status_code = getattr(route, "status_code", None) or 200
        body = None if result is None else jsonable_encoder(result)
        return StoredResponse(status_code=status_code, body=body)


def _to_http_response(result: IdempotentResult) -> Response:
    # La primera respuesta también sale de aquí, para que la original y la del
    # reintento se generen igual a partir del mismo JSON.
    response = result.response
    headers = {IDEMPOTENT_REPLAYED_HEADER: "true"} if result.replayed else None
    if response.status_code == 204:
        return Response(status_code=204, headers=headers)
    return JSONResponse(
        content=response.body, status_code=response.status_code, headers=headers
    )


async def _request_hash(request: Request) -> str:
    # FastAPI ya leyó y cacheó el cuerpo para validarlo; `body()` devuelve esos
    # mismos bytes. La consulta (query string) no forma parte del hash.
    digest = hashlib.sha256()
    digest.update(f"{request.method} {request.url.path}\n".encode())
    digest.update(await request.body())
    return digest.hexdigest()


def get_idempotency_service(
    repository: IdempotencyRepository = Depends(get_idempotency_repository),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> IdempotencyService:
    return IdempotencyService(repository, uow)


async def require_idempotency_key(
    request: Request,
    idempotency_key: UUID = Header(
        alias=IDEMPOTENCY_KEY_HEADER, description=_HEADER_DESCRIPTION
    ),
    service: IdempotencyService = Depends(get_idempotency_service),
) -> Idempotency:
    """Obligatoria en los POST que crean recursos o mueven dinero.

    Si falta o no es un UUID, FastAPI responde 422 `VALIDATION_ERROR`.
    """
    return Idempotency(
        request, service, str(idempotency_key), await _request_hash(request)
    )


async def accept_idempotency_key(
    request: Request,
    idempotency_key: UUID | None = Header(
        default=None, alias=IDEMPOTENCY_KEY_HEADER, description=_HEADER_DESCRIPTION
    ),
    service: IdempotencyService = Depends(get_idempotency_service),
) -> Idempotency:
    """Opcional en PUT/PATCH/DELETE: si llega, se aplica la misma protección."""
    if idempotency_key is None:
        return Idempotency(request, service, None, None)
    return Idempotency(
        request, service, str(idempotency_key), await _request_hash(request)
    )
