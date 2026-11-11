from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from domain.repositories.auth.auth_event_repository import AuthEventRepository
from domain.repositories.auth.password_reset_token_repository import (
    PasswordResetTokenRepository,
)
from domain.repositories.auth.pending_signup_repository import PendingSignupRepository
from domain.repositories.auth.session_repository import SessionRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from shared.utils.time import utc_now

SESSION_RETENTION = timedelta(days=30)
AUTH_EVENT_RETENTION = timedelta(days=90)


@dataclass(frozen=True)
class PurgeAuthDataResult:
    sessions: int
    events: int
    pending_signups: int = 0
    password_reset_tokens: int = 0


class PurgeAuthDataHandler:
    """Job diario: borra las sesiones vencidas o revocadas hace más de 30 días (con sus
    refresh tokens), los eventos de auditoría de más de 90 días, los registros sin confirmar
    ya caducados (con sus enlaces) y los enlaces de recuperación vencidos o usados."""

    def __init__(
        self,
        session_repository: SessionRepository,
        auth_event_repository: AuthEventRepository,
        uow: AbstractUnitOfWork,
        now: Callable[[], datetime] = utc_now,
        *,
        pending_signup_repository: PendingSignupRepository | None = None,
        reset_token_repository: PasswordResetTokenRepository | None = None,
    ):
        self.session_repository = session_repository
        self.auth_event_repository = auth_event_repository
        self.pending_signup_repository = pending_signup_repository
        self.reset_token_repository = reset_token_repository
        self.uow = uow
        self._now = now

    async def handle(self) -> PurgeAuthDataResult:
        now = self._now()
        pending_signups = reset_tokens = 0
        async with self.uow:
            sessions = await self.session_repository.purge(
                expired_before=now - SESSION_RETENTION,
                revoked_before=now - SESSION_RETENTION,
            )
            events = await self.auth_event_repository.purge(
                created_before=now - AUTH_EVENT_RETENTION
            )
            if self.pending_signup_repository is not None:
                pending_signups = await self.pending_signup_repository.purge(
                    expired_before=now
                )
            if self.reset_token_repository is not None:
                reset_tokens = await self.reset_token_repository.purge(
                    expired_before=now, used_before=now
                )
            await self.uow.commit()
        return PurgeAuthDataResult(
            sessions=sessions,
            events=events,
            pending_signups=pending_signups,
            password_reset_tokens=reset_tokens,
        )
