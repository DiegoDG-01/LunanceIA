from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from domain.entities.auth.session import UserSession
from domain.repositories.auth.session_repository import SessionRepository
from shared.utils.time import utc_now


@dataclass
class ListSessionsQuery:
    user_id: int
    current_session_uuid: str | None = None


@dataclass(frozen=True)
class SessionView:
    session: UserSession
    is_current: bool


class ListSessionsHandler:
    def __init__(
        self,
        session_repository: SessionRepository,
        now: Callable[[], datetime] = utc_now,
    ):
        self.session_repository = session_repository
        self._now = now

    async def handle(self, query: ListSessionsQuery) -> list[SessionView]:
        sessions = await self.session_repository.list_active(query.user_id, self._now())
        return [
            SessionView(
                session=session,
                is_current=session.uuid == query.current_session_uuid,
            )
            for session in sessions
        ]
