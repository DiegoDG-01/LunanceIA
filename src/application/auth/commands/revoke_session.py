from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from application.auth.dto import ClientContext
from application.auth.services.sessions import record_revocation
from application.interfaces.auth_service import SessionRevocationList
from domain.entities.auth.session import RevocationReason
from domain.repositories.auth.auth_event_repository import AuthEventRepository
from domain.repositories.auth.session_repository import SessionRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from shared.exceptions.domain import SessionNotFoundError
from shared.utils.time import utc_now


@dataclass
class RevokeSessionCommand:
    user_id: int
    session_uuid: str
    # Sesión desde la que se pide el cierre (la del access token).
    actor_session_uuid: str | None = None
    context: ClientContext = field(default_factory=ClientContext)


class RevokeSessionHandler:
    """`DELETE /auth/sessions/{uuid}`: solo sesiones propias y abiertas; el resto responde 404."""

    def __init__(
        self,
        session_repository: SessionRepository,
        auth_event_repository: AuthEventRepository,
        revocations: SessionRevocationList,
        uow: AbstractUnitOfWork,
        now: Callable[[], datetime] = utc_now,
    ):
        self.session_repository = session_repository
        self.auth_event_repository = auth_event_repository
        self.revocations = revocations
        self.uow = uow
        self._now = now

    async def handle(self, command: RevokeSessionCommand) -> None:
        async with self.uow:
            session = await self.session_repository.get_by_uuid(
                command.session_uuid, for_update=True
            )
            now = self._now()
            if (
                session is None
                or session.user_id != command.user_id
                or not session.is_active(now)
            ):
                raise SessionNotFoundError(command.session_uuid)
            session.revoke(now, RevocationReason.REVOKED_BY_USER)
            await self.session_repository.save(session)
            await record_revocation(
                self.auth_event_repository,
                session,
                now=now,
                revoked_by="user",
                context=command.context,
                actor_session_uuid=command.actor_session_uuid,
            )
            await self.uow.commit()
        await self.revocations.revoke([session.uuid])
