"""Rate limits con ventana fija sobre Redis.

Cada regla cuenta peticiones por (identidad, ruta) dentro de una ventana de tiempo fija: un
`INCR` + `EXPIRE` atómico por petición. Los nombres `limiter_N_per_X` son exactos: N peticiones
por minuto, hora o día.

Si Redis no responde, cada llamada decide: `fail_closed=True` (login, registro, recuperación
de contraseña) responde 503 para no quitar la protección contra fuerza bruta; el resto deja
pasar la petición y lo registra en el log.
"""

import logging
import math
import time
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import HTTPException, Request
from redis.asyncio import Redis
from redis.exceptions import RedisError

from infrastructure.cache.redis import get_redis
from infrastructure.config.settings import settings
from infrastructure.rate_limiting.client_ip import ip_identity

logger = logging.getLogger(__name__)

UNAVAILABLE_RETRY_AFTER = 5

_UNITS = {86400: "day", 3600: "hour", 60: "minute", 1: "second"}


@dataclass(frozen=True, slots=True)
class RateLimitRule:
    limit: int
    window_seconds: int

    def __post_init__(self) -> None:
        if self.limit <= 0 or self.window_seconds <= 0:
            raise ValueError("limit y window_seconds deben ser positivos")

    @property
    def description(self) -> str:
        unit = _UNITS.get(self.window_seconds)
        if unit is None:
            return f"{self.limit} per {self.window_seconds} seconds"
        return f"{self.limit} per 1 {unit}"


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after: int = 0


class RateLimiterUnavailable(Exception):
    """Redis no respondió: no se sabe si la petición entra en el límite."""


class RedisRateLimiter:
    def __init__(
        self,
        redis: Callable[[], Redis],
        *,
        prefix: str = "rl",
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._redis = redis
        self._prefix = prefix
        self._clock = clock

    async def hit(self, key: str, rule: RateLimitRule) -> RateLimitDecision:
        now = self._clock()
        window = int(now // rule.window_seconds)
        # La regla va en la clave: dos límites distintos sobre la misma ruta no comparten contador.
        redis_key = f"{self._prefix}:{rule.limit}/{rule.window_seconds}:{key}:{window}"
        try:
            async with self._redis().pipeline(transaction=True) as pipe:
                pipe.incr(redis_key)
                pipe.expire(redis_key, rule.window_seconds, nx=True)
                count, _ = await pipe.execute()
        except (RedisError, OSError, RuntimeError) as error:
            raise RateLimiterUnavailable from error

        if count <= rule.limit:
            return RateLimitDecision(allowed=True, remaining=rule.limit - count)
        retry_after = max(1, math.ceil((window + 1) * rule.window_seconds - now))
        return RateLimitDecision(allowed=False, remaining=0, retry_after=retry_after)


rate_limiter = RedisRateLimiter(get_redis)

limiter_1_per_day = RateLimitRule(limit=1, window_seconds=86400)
limiter_2_per_day = RateLimitRule(limit=2, window_seconds=86400)
limiter_5_per_hour = RateLimitRule(limit=5, window_seconds=3600)
limiter_5_per_minute = RateLimitRule(limit=5, window_seconds=60)
limiter_10_per_minute = RateLimitRule(limit=10, window_seconds=60)
limiter_15_per_minute = RateLimitRule(limit=15, window_seconds=60)
limiter_20_per_minute = RateLimitRule(limit=20, window_seconds=60)
limiter_30_per_minute = RateLimitRule(limit=30, window_seconds=60)
limiter_50_per_minute = RateLimitRule(limit=50, window_seconds=60)
limiter_100_per_minute = RateLimitRule(limit=100, window_seconds=60)
limiter_auth_failure = RateLimitRule(limit=20, window_seconds=60)
# Correos por buzón (clave = hash del correo, no la IP): nadie llena de enlaces la bandeja
# de otro. Cuentan igual tenga o no cuenta el correo, así que no revelan nada.
limiter_signup_emails = RateLimitRule(limit=5, window_seconds=3600)
limiter_password_reset_emails = RateLimitRule(limit=3, window_seconds=3600)


async def enforce_rate_limit(
    limiter: RateLimitRule,
    request: Request,
    *,
    key: str | None = None,
    fail_closed: bool = False,
) -> None:
    if settings.ENVIRONMENT.upper() == "TEST":
        return

    if key is None:
        # Si la petición está autenticada, limita por usuario (no por IP): el tráfico
        # vía MCP llega siempre como 127.0.0.1 y compartiría un único contador.
        principal = getattr(request.state, "rate_limit_id", None) or ip_identity(
            request
        )
        key = f"{principal}:{request.url.path}"

    try:
        decision = await rate_limiter.hit(key, limiter)
    except RateLimiterUnavailable:
        if fail_closed:
            logger.error(
                "Rate limiter unavailable; rejecting request", extra={"key": key}
            )
            raise HTTPException(
                status_code=503,
                detail="Service temporarily unavailable",
                headers={"Retry-After": str(UNAVAILABLE_RETRY_AFTER)},
            ) from None
        logger.warning("Rate limiter unavailable; allowing request", extra={"key": key})
        return

    if not decision.allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {limiter.description}",
            headers={
                "Retry-After": str(decision.retry_after),
                "X-RateLimit-Remaining": "0",
            },
        )
