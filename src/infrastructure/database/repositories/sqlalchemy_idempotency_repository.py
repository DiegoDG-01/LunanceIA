import logging
from datetime import datetime
from typing import Any, cast

from sqlalchemy import CursorResult, delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from application.interfaces.idempotency import (
    IdempotencyRecord,
    IdempotencyRepository,
    StoredResponse,
)
from infrastructure.database.models.idempotency_key import IdempotencyKeyModel

logger = logging.getLogger(__name__)


class SQLAlchemyIdempotencyRepository(IdempotencyRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def try_claim(
        self, *, user_id: int, key: str, request_hash: str, created_at: datetime
    ) -> bool:
        # INSERT directo (no ORM) para que el duplicado salga aquí y no en un flush
        # posterior. En InnoDB, si otra transacción tiene la misma clave sin confirmar,
        # este INSERT espera a que termine: así dos reintentos simultáneos nunca
        # ejecutan la operación dos veces.
        try:
            await self.db.execute(
                insert(IdempotencyKeyModel).values(
                    user_id=user_id,
                    key=key,
                    request_hash=request_hash,
                    created_at=created_at,
                )
            )
        except IntegrityError:
            return False
        return True

    async def get(self, *, user_id: int, key: str) -> IdempotencyRecord | None:
        row = (
            await self.db.execute(
                select(
                    IdempotencyKeyModel.request_hash,
                    IdempotencyKeyModel.status_code,
                    IdempotencyKeyModel.response,
                ).where(
                    IdempotencyKeyModel.user_id == user_id,
                    IdempotencyKeyModel.key == key,
                )
            )
        ).one_or_none()
        if row is None:
            return None
        response = None
        if row.status_code is not None:
            response = StoredResponse(status_code=row.status_code, body=row.response)
        return IdempotencyRecord(request_hash=row.request_hash, response=response)

    async def save_response(
        self,
        *,
        user_id: int,
        key: str,
        request_hash: str,
        response: StoredResponse,
        created_at: datetime,
    ) -> None:
        result = cast(
            CursorResult[Any],
            await self.db.execute(
                update(IdempotencyKeyModel)
                .where(
                    IdempotencyKeyModel.user_id == user_id,
                    IdempotencyKeyModel.key == key,
                )
                .values(status_code=response.status_code, response=response.body)
            ),
        )
        if result.rowcount == 0:
            # Solo pasa si el handler hizo rollback de su propia transacción (con la
            # clave dentro) y aun así confirmó un cambio después. Se guarda igualmente
            # para que los reintentos no lo repitan.
            logger.warning(
                "Idempotency-Key reservada no encontrada al guardar la respuesta "
                "(user_id=%s); se inserta de nuevo",
                user_id,
            )
            await self.db.execute(
                insert(IdempotencyKeyModel).values(
                    user_id=user_id,
                    key=key,
                    request_hash=request_hash,
                    status_code=response.status_code,
                    response=response.body,
                    created_at=created_at,
                )
            )

    async def purge(self, *, created_before: datetime) -> int:
        result = cast(
            CursorResult[Any],
            await self.db.execute(
                delete(IdempotencyKeyModel).where(
                    IdempotencyKeyModel.created_at < created_before
                )
            ),
        )
        return result.rowcount
