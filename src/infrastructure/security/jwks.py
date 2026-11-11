"""Claves públicas (JWKS) de un proveedor de identidad, en caché.

Google y Apple firman sus ID tokens con claves que publican y rotan. Aquí se guardan lo que
indica su `Cache-Control: max-age` y se vuelven a pedir antes si llega un `kid` desconocido,
pero no más de una vez por `min_refresh_interval`: un token inventado no convierte cada
petición en una llamada al proveedor.
"""

import asyncio
import logging
import re
import time
from collections.abc import Callable

import httpx
import jwt

logger = logging.getLogger(__name__)

_MAX_AGE = re.compile(r"max-age=(\d+)")
# Sin Cache-Control se guardan una hora; los proveedores rotan las claves con días de margen.
DEFAULT_KEYS_TTL_SECONDS = 3600
# Ni un max-age enorme deja una clave revocada en caché más de un día.
MAX_KEYS_TTL_SECONDS = 24 * 3600
MIN_REFRESH_INTERVAL_SECONDS = 60


class KeysUnavailable(Exception):
    """No se pudieron obtener las claves y no queda ninguna vigente."""


class JwksCache:
    def __init__(
        self,
        url: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 5.0,
        clock: Callable[[], float] = time.monotonic,
        min_refresh_interval: float = MIN_REFRESH_INTERVAL_SECONDS,
    ) -> None:
        self._url = url
        # Para tests: `httpx.MockTransport`. Sin él, un cliente nuevo por descarga (son pocas).
        self._transport = transport
        self._timeout = timeout
        self._clock = clock
        self._min_refresh_interval = min_refresh_interval
        self._keys: dict[str, jwt.PyJWK] = {}
        self._expires_at = 0.0
        self._fetched_at: float | None = None
        self._lock = asyncio.Lock()

    async def key(self, kid: str) -> jwt.PyJWK | None:
        """La clave `kid`, o None si el proveedor no la publica."""
        async with self._lock:
            now = self._clock()
            stale = now >= self._expires_at
            unknown = kid not in self._keys and (
                self._fetched_at is None
                or now - self._fetched_at >= self._min_refresh_interval
            )
            if stale or unknown:
                await self._fetch(now)
            return self._keys.get(kid)

    async def _fetch(self, now: float) -> None:
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, transport=self._transport
            ) as client:
                response = await client.get(self._url)
            response.raise_for_status()
            key_set = jwt.PyJWKSet.from_dict(response.json())
        except (httpx.HTTPError, ValueError, jwt.PyJWTError) as error:
            # Aunque falle, cuenta como intento: no se reintenta en cada petición.
            self._fetched_at = now
            if self._keys and now < self._expires_at:
                logger.warning(
                    "JWKS refresh failed; keeping cached keys",
                    extra={"url": self._url},
                    exc_info=True,
                )
                return
            raise KeysUnavailable(self._url) from error
        self._keys = {key.key_id: key for key in key_set.keys if key.key_id}
        self._fetched_at = now
        self._expires_at = now + _max_age(response.headers.get("cache-control", ""))


def _max_age(cache_control: str) -> int:
    match = _MAX_AGE.search(cache_control)
    ttl = int(match.group(1)) if match else DEFAULT_KEYS_TTL_SECONDS
    return min(ttl, MAX_KEYS_TTL_SECONDS)
