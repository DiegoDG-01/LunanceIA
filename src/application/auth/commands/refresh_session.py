import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import cast

from application.auth.config import AuthConfig
from application.auth.dto import ClientContext, IssuedSession
from application.auth.services.sessions import SessionManager, record_revocation
from application.interfaces.auth_service import SessionRevocationList
from domain.entities.auth.auth_event import AuthAction, AuthEvent
from domain.entities.auth.session import RevocationReason
from domain.repositories.auth.auth_event_repository import AuthEventRepository
from domain.repositories.auth.refresh_token_repository import RefreshTokenRepository
from domain.repositories.auth.session_repository import SessionRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from domain.repositories.users.user_repository import UserRepository
from shared.exceptions.domain import SessionExpiredError
from shared.utils.time import utc_now
from shared.utils.tokens import hash_token, refresh_successor

logger = logging.getLogger(__name__)


@dataclass
class RefreshSessionCommand:
    refresh_token: str
    context: ClientContext


class RefreshSessionHandler:
    """`POST /auth/refresh`: canjea el refresh token por su sucesor (rotación).

    - Un refresh normal solo renueva la inactividad de la sesión (`last_seen_at`, `last_ip`).
    - Repetir un token recién canjeado (dentro del margen de gracia) devuelve el mismo
      sucesor: la respuesta anterior se perdió por la red.
    - Repetirlo fuera del margen significa que alguien más lo tiene: se revoca la sesión entera
      de ese dispositivo (`refresh_reuse`).
    """

    def __init__(
        self,
        user_repository: UserRepository,
        session_repository: SessionRepository,
        refresh_token_repository: RefreshTokenRepository,
        auth_event_repository: AuthEventRepository,
        session_manager: SessionManager,
        revocations: SessionRevocationList,
        uow: AbstractUnitOfWork,
        config: AuthConfig,
        now: Callable[[], datetime] = utc_now,
    ):
        self.user_repository = user_repository
        self.session_repository = session_repository
        self.refresh_token_repository = refresh_token_repository
        self.auth_event_repository = auth_event_repository
        self.session_manager = session_manager
        self.revocations = revocations
        self.uow = uow
        self.config = config
        self._now = now

    async def handle(self, command: RefreshSessionCommand) -> IssuedSession:
        if not command.refresh_token:
            raise SessionExpiredError("Refresh token missing")

        token_hash = hash_token(command.refresh_token)
        async with self.uow:
            token = await self.refresh_token_repository.get(token_hash)
            if token is None:
                raise SessionExpiredError("Unknown refresh token")
            # FOR UPDATE: dos refresh simultáneos de la misma sesión se aplican de uno en uno.
            session = await self.session_repository.get(
                token.session_id, for_update=True
            )
            now = self._now()
            if session is None or not session.is_active(now):
                raise SessionExpiredError()
            # Se vuelve a leer con el lock tomado: otro refresh pudo rotarlo mientras tanto.
            token = await self.refresh_token_repository.get(token_hash, for_update=True)
            if token is None:
                raise SessionExpiredError("Unknown refresh token")
            if (
                session.device_id != command.context.device_id
                or session.platform != command.context.platform
            ):
                logger.warning(
                    "Refresh from a different device or platform",
                    extra={"session_uuid": session.uuid},
                )
                raise SessionExpiredError("Device mismatch")

            if (
                token.rotated_at is not None
                and now - token.rotated_at > self.config.refresh_reuse_grace
            ):
                session.revoke(now, RevocationReason.REFRESH_REUSE)
                await self.session_repository.save(session)
                await self.auth_event_repository.record(
                    AuthEvent(
                        action=AuthAction.SESSION_REFRESH_REUSE_DETECTED,
                        created_at=now,
                        user_id=session.user_id,
                        session_id=session.id,
                        ip=command.context.ip,
                        user_agent=command.context.user_agent,
                        details={"session_uuid": session.uuid},
                    )
                )
                await record_revocation(
                    self.auth_event_repository,
                    session,
                    now=now,
                    revoked_by="system",
                    context=command.context,
                )
                await self.uow.commit()
                await self.revocations.revoke([session.uuid])
                logger.warning(
                    "Refresh token reuse detected; session revoked",
                    extra={"session_uuid": session.uuid},
                )
                raise SessionExpiredError("Refresh token reuse")

            user = await self.user_repository.get_by_id(session.user_id)
            if user is None or not user.is_active:
                raise SessionExpiredError("User not found or inactive")

            next_token = refresh_successor(
                command.refresh_token, key=self.config.refresh_rotation_key
            )
            if token.rotated_at is not None:
                # Reintento dentro del margen: se repite el mismo sucesor, solo mientras siga
                # vigente. No se resucita un refresh que ya se volvió a rotar ni se crean ramas.
                # Lectura con bloqueo: la normal vería la foto de la transacción, tomada
                # quizá antes de que el refresh concurrente confirmara el sucesor.
                successor = await self.refresh_token_repository.get(
                    hash_token(next_token), for_update=True
                )
                if (
                    successor is None
                    or successor.session_id != session.id
                    or successor.rotated_at is not None
                ):
                    raise SessionExpiredError("Refresh token already rotated")
                await self.uow.commit()
                return self.session_manager.access_pair(
                    session, user_uuid=user.uuid, refresh_token=next_token
                )

            # También retira cualquier otro token vigente de la sesión: nunca hay ramas.
            await self.refresh_token_repository.rotate_active(
                cast(int, session.id), now
            )
            session.touch(
                now, self.config.lifetime_for(session.platform).idle, command.context.ip
            )
            if command.context.client:
                session.client = command.context.client
            if command.context.user_agent:
                session.user_agent = command.context.user_agent
            await self.session_repository.save(session)
            issued = await self.session_manager.issue(
                session, user_uuid=user.uuid, now=now, refresh_token=next_token
            )
            await self.uow.commit()
        return issued
