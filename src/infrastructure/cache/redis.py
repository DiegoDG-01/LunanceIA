"""Cliente de Redis compartido por toda la app (rate limits y, desde la fase 1, sesiones).

Se abre en el `lifespan` de la app y se cierra al apagarla. Crear el cliente no conecta: la
primera operación lo hace, así que la app arranca aunque Redis no esté disponible y cada uso
decide qué hacer si falla.
"""

import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

_client: Redis | None = None


def init_redis(url: str) -> Redis:
    global _client
    _client = Redis.from_url(
        url,
        decode_responses=True,
        health_check_interval=30,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
    return _client


def set_redis(client: Redis | None) -> None:
    """Para tests: sustituye el cliente (por ejemplo, por uno de fakeredis)."""
    global _client
    _client = client


def get_redis() -> Redis:
    if _client is None:
        raise RuntimeError(
            "Redis no está inicializado: llama a init_redis() en el lifespan."
        )
    return _client


async def ping_redis() -> bool:
    try:
        return bool(await get_redis().ping())
    except (RedisError, RuntimeError, OSError):
        return False


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
