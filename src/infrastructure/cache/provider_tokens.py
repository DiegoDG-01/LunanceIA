"""ID tokens de Google y Apple ya usados, en Redis.

Cada token se apunta por su SHA-256 hasta que caduca (más un margen), así que uno capturado
no abre una segunda sesión mientras siga vigente. Fail-closed: si Redis no responde se lanza
`ServiceTemporarilyUnavailableError` (503), igual que el login con contraseña.
"""

import hashlib
import logging
import math
from collections.abc import Callable
from datetime import datetime

from redis.asyncio import Redis
from redis.exceptions import RedisError

from application.interfaces.identity_providers import UsedProviderTokens
from shared.exceptions.application import ServiceTemporarilyUnavailableError
from shared.utils.time import utc_now

logger = logging.getLogger(__name__)

# El leeway de la verificación más un margen: mientras el token pase la comprobación de `exp`,
# su marca sigue en Redis.
MARGIN_SECONDS = 120
# Tope por si un proveedor emitiera tokens larguísimos: Google da 1 h y Apple 10 min.
MAX_TTL_SECONDS = 24 * 3600


class RedisUsedProviderTokens(UsedProviderTokens):
    def __init__(
        self,
        redis: Callable[[], Redis],
        *,
        prefix: str = "provider_token",
        now: Callable[[], datetime] = utc_now,
    ) -> None:
        self._redis = redis
        self._prefix = prefix
        self._now = now

    async def claim(self, token: str, *, expires_at: datetime) -> bool:
        digest = hashlib.sha256(token.encode()).hexdigest()
        remaining = (expires_at - self._now()).total_seconds()
        ttl = min(max(math.ceil(remaining), 0) + MARGIN_SECONDS, MAX_TTL_SECONDS)
        try:
            return bool(
                await self._redis().set(
                    f"{self._prefix}:{digest}", "1", nx=True, ex=ttl
                )
            )
        except (RedisError, OSError, RuntimeError) as error:
            logger.error("Used provider tokens unavailable; rejecting sign in")
            raise ServiceTemporarilyUnavailableError("redis") from error
