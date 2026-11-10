from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from domain.repositories.auth.auth_event_repository import AuthEventRepository
from domain.repositories.auth.session_repository import SessionRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from shared.utils.time import utc_now

SESSION_RETENTION = timedelta(days=30)
AUTH_EVENT_RETENTION = timedelta(days=90)


@dataclass(frozen=True)
class PurgeAuthDataResult:
    sessions: int
    events: int


class PurgeAuthDataHandler:
    """Job diario: borra las sesiones vencidas o revocadas hace más de 30 días (con sus
    refresh tokens) y los eventos de auditoría de más de 90 días."""

    def __init__(
        self,
        session_repository: SessionRepository,
        auth_event_repository: AuthEventRepository,
        uow: AbstractUnitOfWork,
        now: Callable[[], datetime] = utc_now,
    ):
        self.session_repository = session_repository
        self.auth_event_repository = auth_event_repository
        self.uow = uow
        self._now = now

    async def handle(self) -> PurgeAuthDataResult:
        now = self._now()
        async with self.uow:
            sessions = await self.session_repository.purge(
                expired_before=now - SESSION_RETENTION,
                revoked_before=now - SESSION_RETENTION,
            )
            events = await self.auth_event_repository.purge(
                created_before=now - AUTH_EVENT_RETENTION
            )
            await self.uow.commit()
        return PurgeAuthDataResult(sessions=sessions, events=events)
