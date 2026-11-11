"""Bloqueo progresivo del login por correo (+ IP) en Redis.

Tras `free_attempts` fallos seguidos el sujeto se bloquea `base_lock_seconds`, y cada fallo
más duplica el bloqueo hasta `max_lock_seconds`. Un inicio de sesión correcto lo reinicia.
El correo nunca llega a Redis en claro: la clave es un SHA-256 del sujeto.

Si Redis no responde se lanza `ServiceTemporarilyUnavailableError` (503): el login no se
atiende sin su protección contra fuerza bruta.
"""

import hashlib
import logging
from collections.abc import Callable

from redis.asyncio import Redis
from redis.exceptions import RedisError

from application.interfaces.auth_service import LoginThrottle
from shared.exceptions.application import ServiceTemporarilyUnavailableError

logger = logging.getLogger(__name__)

_REDIS_ERRORS = (RedisError, OSError, RuntimeError)


class RedisLoginThrottle(LoginThrottle):
    FREE_ATTEMPTS = 5
    BASE_LOCK_SECONDS = 60
    MAX_LOCK_SECONDS = 15 * 60
    FAILURE_WINDOW_SECONDS = 60 * 60
    # Tope por correo, desde las IPs que sean: 30 fallos en una hora bloquean 15 min.
    ACCOUNT_FREE_ATTEMPTS = 30

    def __init__(
        self,
        redis: Callable[[], Redis],
        *,
        prefix: str = "login",
        free_attempts: int = FREE_ATTEMPTS,
        base_lock_seconds: int = BASE_LOCK_SECONDS,
        max_lock_seconds: int = MAX_LOCK_SECONDS,
        failure_window_seconds: int = FAILURE_WINDOW_SECONDS,
    ) -> None:
        self._redis = redis
        self._prefix = prefix
        self._free_attempts = free_attempts
        self._base_lock = base_lock_seconds
        self._max_lock = max_lock_seconds
        self._window = failure_window_seconds

    @classmethod
    def per_account(cls, redis: Callable[[], Redis]) -> "RedisLoginThrottle":
        return cls(
            redis,
            prefix="login_account",
            free_attempts=cls.ACCOUNT_FREE_ATTEMPTS,
            base_lock_seconds=cls.MAX_LOCK_SECONDS,
        )

    def _keys(self, subject: str) -> tuple[str, str]:
        digest = hashlib.sha256(subject.encode()).hexdigest()[:32]
        return f"{self._prefix}:fail:{digest}", f"{self._prefix}:lock:{digest}"

    @staticmethod
    def _unavailable(error: Exception) -> ServiceTemporarilyUnavailableError:
        logger.error("Login throttle unavailable; rejecting login", exc_info=error)
        return ServiceTemporarilyUnavailableError("redis")

    async def retry_after(self, subject: str) -> int | None:
        _, lock_key = self._keys(subject)
        try:
            ttl = await self._redis().ttl(lock_key)
        except _REDIS_ERRORS as error:
            raise self._unavailable(error) from error
        return ttl if ttl > 0 else None

    async def record_failure(self, subject: str) -> None:
        fail_key, lock_key = self._keys(subject)
        try:
            async with self._redis().pipeline(transaction=True) as pipe:
                pipe.incr(fail_key)
                pipe.expire(fail_key, self._window)
                failures, _ = await pipe.execute()
            if failures >= self._free_attempts:
                lock = self._base_lock * 2 ** min(failures - self._free_attempts, 4)
                await self._redis().set(lock_key, "1", ex=min(lock, self._max_lock))
        except _REDIS_ERRORS as error:
            raise self._unavailable(error) from error

    async def reset(self, subject: str) -> None:
        try:
            await self._redis().delete(*self._keys(subject))
        except _REDIS_ERRORS as error:
            raise self._unavailable(error) from error
