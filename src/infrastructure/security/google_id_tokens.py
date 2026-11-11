"""ID tokens de "Iniciar sesión con Google" (web, iOS y Android).

La app obtiene el token con el SDK de Google y lo manda tal cual; aquí se comprueba con las
claves públicas de Google en caché, sin llamar a Google en cada login
(https://developers.google.com/identity/openid-connect/openid-connect#validatinganidtoken).
"""

import time
from collections.abc import Callable, Iterable
from datetime import UTC, datetime

import httpx

from application.interfaces.identity_providers import (
    GoogleTokenVerifier,
    IdentityProvider,
    ProviderIdentity,
)
from infrastructure.security.id_tokens import check_nonce, decode_provider_jwt, is_true
from infrastructure.security.jwks import JwksCache
from shared.exceptions.application import InvalidProviderTokenError

CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
ISSUERS = ("https://accounts.google.com", "accounts.google.com")
_PROVIDER = IdentityProvider.GOOGLE.value


class GoogleIdTokenVerifier(GoogleTokenVerifier):
    def __init__(
        self,
        *,
        client_ids: Iterable[str],
        transport: httpx.AsyncBaseTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._audiences = [client_id for client_id in client_ids if client_id]
        if not self._audiences:
            raise ValueError("GoogleIdTokenVerifier necesita al menos un client ID")
        self._keys = JwksCache(CERTS_URL, transport=transport, clock=clock)

    async def verify(self, id_token: str, *, nonce: str | None) -> ProviderIdentity:
        claims = await decode_provider_jwt(
            id_token,
            provider=_PROVIDER,
            keys=self._keys,
            audiences=self._audiences,
            issuers=ISSUERS,
            required=("exp", "iat", "iss", "aud", "sub"),
        )
        check_nonce(claims, nonce, provider=_PROVIDER)
        email = claims.get("email")
        if not isinstance(email, str) or not email:
            raise InvalidProviderTokenError(_PROVIDER, "email_missing")
        if not is_true(claims.get("email_verified")):
            raise InvalidProviderTokenError(_PROVIDER, "email_not_verified")
        name = claims.get("name")
        hosted_domain = claims.get("hd")
        return ProviderIdentity(
            provider=IdentityProvider.GOOGLE,
            subject=str(claims["sub"]),
            audience=str(claims["aud"]),
            expires_at=datetime.fromtimestamp(int(claims["exp"]), UTC),
            email=email,
            name=name if isinstance(name, str) and name.strip() else None,
            hosted_domain=hosted_domain.lower()
            if isinstance(hosted_domain, str) and hosted_domain
            else None,
        )
