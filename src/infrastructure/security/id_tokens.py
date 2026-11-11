"""Comprobación común de los ID tokens de Google y Apple (JWT RS256 firmados con su JWKS).

Cada fallo lanza `InvalidProviderTokenError` con un motivo corto para la auditoría
(`signature`, `audience`, `expired`…); la respuesta al cliente es siempre la misma.
"""

import hashlib
import hmac
from collections.abc import Sequence
from typing import Any

import jwt

from infrastructure.security.jwks import JwksCache, KeysUnavailable
from shared.exceptions.application import (
    IdentityProviderUnavailableError,
    InvalidProviderTokenError,
)

ALGORITHM = "RS256"
# Margen para la diferencia de reloj con el proveedor (exp, iat).
LEEWAY_SECONDS = 10
# Un ID token nunca debería medir esto; cortar antes evita decodificar basura enorme.
MAX_TOKEN_LENGTH = 8192


def nonce_digest(nonce: str) -> str:
    """La app manda al proveedor el SHA-256 (hex) del nonce y a nosotros el valor en claro:
    un token interceptado no sirve sin el nonce original."""
    return hashlib.sha256(nonce.encode()).hexdigest()


async def decode_provider_jwt(
    token: str,
    *,
    provider: str,
    keys: JwksCache,
    audiences: Sequence[str],
    issuers: Sequence[str],
    required: Sequence[str],
    leeway: int = LEEWAY_SECONDS,
) -> dict[str, Any]:
    """Las claims de un JWT firmado por el proveedor para una de nuestras audiencias."""
    if not token or len(token) > MAX_TOKEN_LENGTH:
        raise InvalidProviderTokenError(provider, "malformed")
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError:
        raise InvalidProviderTokenError(provider, "malformed") from None
    kid = header.get("kid")
    if header.get("alg") != ALGORITHM:
        raise InvalidProviderTokenError(provider, "algorithm")
    if not isinstance(kid, str) or not kid:
        raise InvalidProviderTokenError(provider, "malformed")
    try:
        key = await keys.key(kid)
    except KeysUnavailable as error:
        raise IdentityProviderUnavailableError(provider) from error
    if key is None:
        raise InvalidProviderTokenError(provider, "unknown_key")
    try:
        return jwt.decode(
            token,
            key.key,
            algorithms=[ALGORITHM],
            audience=list(audiences),
            issuer=list(issuers),
            leeway=leeway,
            options={"require": list(required)},
        )
    except jwt.ExpiredSignatureError:
        reason = "expired"
    except jwt.ImmatureSignatureError:
        reason = "issued_in_future"
    except jwt.InvalidAudienceError:
        reason = "audience"
    except jwt.InvalidIssuerError:
        reason = "issuer"
    except jwt.MissingRequiredClaimError:
        reason = "missing_claim"
    except jwt.InvalidSignatureError:
        reason = "signature"
    except jwt.PyJWTError:
        reason = "malformed"
    raise InvalidProviderTokenError(provider, reason)


def check_nonce(claims: dict[str, Any], nonce: str | None, *, provider: str) -> None:
    """Si el token lleva nonce, hay que mandar el valor en claro; si se manda, el token debe
    llevar su hash. Sin nonce en ninguno de los dos lados, se acepta (el token sigue siendo
    de un solo uso)."""
    claimed = claims.get("nonce")
    if claimed is None and not nonce:
        return
    if not isinstance(claimed, str) or not nonce:
        raise InvalidProviderTokenError(provider, "nonce")
    if not hmac.compare_digest(claimed, nonce_digest(nonce)):
        raise InvalidProviderTokenError(provider, "nonce")


def is_true(value: Any) -> bool:
    """Google y Apple mandan algunos booleanos como texto (`"true"`)."""
    return value is True or value == "true"
