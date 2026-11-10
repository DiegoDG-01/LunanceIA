import base64
import hashlib
import hmac
import secrets

REFRESH_TOKEN_PREFIX = "rt_"
_ENTROPY_BYTES = 32  # 256 bits


def generate_token(prefix: str = "") -> str:
    """Token opaco (refresh token): 256 bits aleatorios en base64url."""
    return prefix + secrets.token_urlsafe(_ENTROPY_BYTES)


def hash_token(token: str) -> str:
    # En la base solo se guarda el hash: una fuga no expone sesiones vivas.
    return hashlib.sha256(token.encode()).hexdigest()


def refresh_successor(token: str, *, key: bytes) -> str:
    """El único sucesor posible de un refresh token, impredecible sin la clave del servidor.

    Como es determinista, un reintento del mismo refresh (la respuesta se perdió por la red)
    puede devolver el mismo sucesor sin haber guardado nunca el token en claro.
    """
    digest = hmac.digest(
        key, b"lunance:refresh-successor:v1\0" + token.encode(), "sha256"
    )
    return REFRESH_TOKEN_PREFIX + base64.urlsafe_b64encode(digest).decode().rstrip("=")
