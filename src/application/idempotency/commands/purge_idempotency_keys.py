from dataclasses import dataclass
from datetime import datetime

from application.idempotency.service import IDEMPOTENCY_TTL
from application.interfaces.idempotency import IdempotencyRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork


@dataclass
class PurgeIdempotencyKeysCommand:
    now: datetime


class PurgeIdempotencyKeysHandler:
    """Borra las `Idempotency-Key` con más de `IDEMPOTENCY_TTL` de antigüedad."""

    def __init__(self, repository: IdempotencyRepository, uow: AbstractUnitOfWork):
        self.repository = repository
        self.uow = uow

    async def handle(self, command: PurgeIdempotencyKeysCommand) -> int:
        async with self.uow:
            deleted = await self.repository.purge(
                created_before=command.now - IDEMPOTENCY_TTL
            )
            await self.uow.commit()
        return deleted
