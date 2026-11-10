"""Revocación inmediata de sesiones.

Un access token sigue firmado y vigente hasta que caduca (10 min), así que cada petición
autenticada pregunta si su sesión (`sid`) se cerró. Redis guarda `revoked_sid:<uuid>` lo que
dura un access token; MySQL es la autoridad: si Redis no responde, perdió una clave o se
reinició, la sesión se consulta en la base.
"""

import logging
from collections.abc import Callable, Iterable
from datetime import datetime

from redis.asyncio import Redis
from redis.exceptions import RedisError

from application.interfaces.auth_service import SessionRevocationList
from domain.repositories.auth.session_repository import SessionRepository
from shared.utils.time import utc_now

logger = logging.getLogger(__name__)

_REDIS_ERRORS = (RedisError, OSError, RuntimeError)


class RedisSessionRevocationList(SessionRevocationList):
    """Cada clave vive lo mismo que un access token: pasado ese tiempo el token caducó solo."""

    def __init__(
        self,
        redis: Callable[[], Redis],
        *,
        ttl_seconds: int,
        prefix: str = "revoked_sid",
    ) -> None:
        self._redis = redis
        self._ttl = ttl_seconds
        self._prefix = prefix

    def _key(self, session_uuid: str) -> str:
        return f"{self._prefix}:{session_uuid}"

    async def revoke(self, session_uuids: Iterable[str]) -> None:
        uuids = list(session_uuids)
        if not uuids:
            return
        try:
            async with self._redis().pipeline(transaction=False) as pipe:
                for session_uuid in uuids:
                    pipe.set(self._key(session_uuid), "1", ex=self._ttl)
                await pipe.execute()
        except _REDIS_ERRORS:
            # La revocación ya está confirmada en MySQL, que se consulta en cada petición.
            logger.exception(
                "Session revocation list unavailable; relying on the database",
                extra={"count": len(uuids)},
            )

    async def is_revoked(self, session_uuid: str) -> bool:
        """True si Redis la tiene como revocada. Lanza `RedisError` si no responde."""
        return bool(await self._redis().exists(self._key(session_uuid)))


class PersistentSessionRevocations(RedisSessionRevocationList):
    """Redis responde primero; la base decide siempre que Redis no la tenga como revocada."""

    def __init__(
        self,
        redis: Callable[[], Redis],
        *,
        ttl_seconds: int,
        session_repository: SessionRepository,
        now: Callable[[], datetime] = utc_now,
    ) -> None:
        super().__init__(redis, ttl_seconds=ttl_seconds)
        self._sessions = session_repository
        self._now = now

    async def is_revoked(self, session_uuid: str) -> bool:
        try:
            if await super().is_revoked(session_uuid):
                return True
        except _REDIS_ERRORS:
            logger.warning(
                "Session revocation list unavailable; checking the database",
                exc_info=True,
            )
        session = await self._sessions.get_by_uuid(session_uuid)
        return session is None or not session.is_active(self._now())
