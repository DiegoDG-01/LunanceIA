"""Cuotas y salud de los proveedores, en Redis.

- Cuotas: contadores de ventana fija con el `RedisRateLimiter` de la app (prefijo `md`),
  reservados antes de cada llamada. Los límites son los del plan gratis de cada proveedor.
- Salud: un proveedor que falló (429, 5xx, timeout) queda marcado `md_down:<proveedor>` y el
  router pasa al siguiente hasta que la marca caduca.

Esto corre en jobs de fondo: si Redis no responde, se sigue sin contar cuotas ni marcas.
"""

import logging
from collections.abc import Callable, Mapping, Sequence

from redis.asyncio import Redis
from redis.exceptions import RedisError

from application.interfaces.market_data import ProviderName, QuotaExhausted
from infrastructure.rate_limiting.limiters import (
    RateLimiterUnavailable,
    RateLimitRule,
    RedisRateLimiter,
)

logger = logging.getLogger(__name__)

DAY = 86400

# Ordenadas de la ventana más corta a la más larga: si se acaba la del minuto, no se gasta
# un lugar de la del día.
DEFAULT_QUOTAS: Mapping[ProviderName, Sequence[RateLimitRule]] = {
    ProviderName.EODHD: (RateLimitRule(limit=20, window_seconds=DAY),),
    ProviderName.TWELVEDATA: (
        RateLimitRule(limit=8, window_seconds=60),
        RateLimitRule(limit=800, window_seconds=DAY),
    ),
    # Sin cuota documentada: límite propio para no llamar la atención.
    ProviderName.YAHOO: (RateLimitRule(limit=30, window_seconds=60),),
    # Límite propio conservador; Banxico no publica uno estricto para el SIE.
    ProviderName.BANXICO: (RateLimitRule(limit=100, window_seconds=300),),
    # DataBursatil cobra por KiB (200,000 créditos al mes), no por llamada: se revisa el
    # saldo con `/v2/creditos` en lugar de contar aquí.
    ProviderName.DATABURSATIL: (),
}

DEFAULT_DOWN_SECONDS = 15 * 60
MAX_DOWN_SECONDS = DAY


class ProviderQuotas:
    def __init__(
        self,
        limiter: RedisRateLimiter,
        rules: Mapping[ProviderName, Sequence[RateLimitRule]] = DEFAULT_QUOTAS,
    ) -> None:
        self._limiter = limiter
        self._rules = {
            name: tuple(sorted(r, key=lambda rule: rule.window_seconds))
            for name, r in rules.items()
        }

    async def reserve(self, provider: ProviderName) -> None:
        """Cuenta una llamada. Lanza `QuotaExhausted` si alguna ventana ya está llena."""
        for rule in self._rules.get(provider, ()):
            try:
                decision = await self._limiter.hit(provider.value, rule)
            except RateLimiterUnavailable:
                logger.warning(
                    "Market data quota unavailable; calling without counting",
                    extra={"provider": provider.value},
                )
                return
            if not decision.allowed:
                raise QuotaExhausted(
                    provider,
                    f"cuota local agotada ({rule.description})",
                    retry_after=decision.retry_after,
                )


class ProviderHealth:
    def __init__(
        self,
        redis: Callable[[], Redis],
        *,
        prefix: str = "md_down",
        down_seconds: int = DEFAULT_DOWN_SECONDS,
    ) -> None:
        self._redis = redis
        self._prefix = prefix
        self._down_seconds = down_seconds

    def _key(self, provider: ProviderName) -> str:
        return f"{self._prefix}:{provider.value}"

    async def is_down(self, provider: ProviderName) -> bool:
        try:
            return bool(await self._redis().exists(self._key(provider)))
        except (RedisError, OSError, RuntimeError):
            return False

    async def mark_down(
        self, provider: ProviderName, seconds: int | None = None, *, reason: str = ""
    ) -> None:
        ttl = min(max(1, seconds or self._down_seconds), MAX_DOWN_SECONDS)
        try:
            await self._redis().set(self._key(provider), reason or "down", ex=ttl)
        except (RedisError, OSError, RuntimeError):
            logger.warning(
                "Could not mark market data provider down",
                extra={"provider": provider.value},
            )
