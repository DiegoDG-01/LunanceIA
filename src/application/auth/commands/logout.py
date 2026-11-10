from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from application.auth.dto import ClientContext
from application.auth.services.sessions import record_revocation
from application.interfaces.auth_service import SessionRevocationList
from domain.entities.auth.session import RevocationReason, UserSession
from domain.repositories.auth.auth_event_repository import AuthEventRepository
from domain.repositories.auth.refresh_token_repository import RefreshTokenRepository
from domain.repositories.auth.session_repository import SessionRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from shared.utils.time import utc_now
from shared.utils.tokens import hash_token


@dataclass
class LogoutCommand:
    refresh_token: str
    all_devices: bool = False
    context: ClientContext = field(default_factory=ClientContext)


@dataclass
class LogoutResponse:
    revoked: int = 0
    message: str = "Logout exitoso"


class LogoutHandler:
    """Cerrar sesión es idempotente: un refresh token desconocido o ya revocado no es error."""

    def __init__(
        self,
        session_repository: SessionRepository,
        refresh_token_repository: RefreshTokenRepository,
        auth_event_repository: AuthEventRepository,
        revocations: SessionRevocationList,
        uow: AbstractUnitOfWork,
        now: Callable[[], datetime] = utc_now,
    ):
        self.session_repository = session_repository
        self.refresh_token_repository = refresh_token_repository
        self.auth_event_repository = auth_event_repository
        self.revocations = revocations
        self.uow = uow
        self._now = now

    async def handle(self, command: LogoutCommand) -> LogoutResponse:
        if not command.refresh_token:
            return LogoutResponse()

        token_hash = hash_token(command.refresh_token)
        async with self.uow:
            token = await self.refresh_token_repository.get(token_hash)
            session = (
                await self.session_repository.get(token.session_id, for_update=True)
                if token
                else None
            )
            now = self._now()
            if session is None or not session.is_active(now):
                return LogoutResponse()
            # Se vuelve a leer con el lock tomado: un refresh concurrente pudo rotarlo.
            token = await self.refresh_token_repository.get(token_hash, for_update=True)
            if token is None:
                return LogoutResponse()

            revoked: list[UserSession]
            # Un refresh cuya respuesta se perdió puede haber rotado el token que conserva la
            # app. Ese token aún sirve para cerrar su sesión, pero no para cerrar las demás.
            if command.all_devices and token.rotated_at is None:
                revoked = await self.session_repository.revoke_active(
                    session.user_id, now, RevocationReason.SIGNED_OUT_EVERYWHERE
                )
            else:
                session.revoke(now, RevocationReason.SIGNED_OUT)
                await self.session_repository.save(session)
                revoked = [session]

            for item in revoked:
                await record_revocation(
                    self.auth_event_repository,
                    item,
                    now=now,
                    revoked_by="user",
                    context=command.context,
                    actor_session_uuid=session.uuid,
                )
            await self.uow.commit()

        await self.revocations.revoke([item.uuid for item in revoked])
        return LogoutResponse(revoked=len(revoked))
