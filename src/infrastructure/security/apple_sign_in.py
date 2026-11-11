"""Sign in with Apple desde el servidor
(https://developer.apple.com/documentation/sign_in_with_apple/sign_in_with_apple_rest_api).

- El identity token se comprueba con las claves públicas de Apple, en caché. La audiencia es
  el bundle ID de la app de iOS o el Services ID de la web (`APPLE_CLIENT_IDS`).
- El código de autorización se canjea por un refresh token firmando un client secret (JWT
  ES256) con la clave .p8. Ese token solo sirve para revocar la autorización al borrar la
  cuenta, como exige Apple (guideline 5.1.1(v)).
- Los avisos servidor a servidor llegan como un JWT firmado con las mismas claves.
"""

import json
import logging
import time
from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ec import (
    SECP256R1,
    EllipticCurvePrivateKey,
)

from application.interfaces.identity_providers import (
    AppleNotification,
    AppleSignInGateway,
    AppleTokens,
    IdentityProvider,
    ProviderIdentity,
)
from infrastructure.security.id_tokens import check_nonce, decode_provider_jwt, is_true
from infrastructure.security.jwks import JwksCache
from shared.exceptions.application import (
    IdentityProviderUnavailableError,
    InvalidProviderTokenError,
)

logger = logging.getLogger(__name__)

ISSUER = "https://appleid.apple.com"
KEYS_URL = "https://appleid.apple.com/auth/keys"
TOKEN_URL = "https://appleid.apple.com/auth/token"
REVOKE_URL = "https://appleid.apple.com/auth/revoke"
PRIVATE_RELAY_DOMAIN = "privaterelay.appleid.com"
# Apple acepta client secrets de hasta 6 meses; se firma uno corto por petición.
CLIENT_SECRET_TTL = timedelta(minutes=5)
_PROVIDER = IdentityProvider.APPLE.value


def load_apple_private_key(pem: str) -> EllipticCurvePrivateKey:
    """La clave .p8 de Sign in with Apple (EC P-256 en PKCS#8)."""
    private_key = serialization.load_pem_private_key(pem.encode(), password=None)
    if not isinstance(private_key, EllipticCurvePrivateKey) or not isinstance(
        private_key.curve, SECP256R1
    ):
        raise TypeError("La clave de Sign in with Apple debe ser la .p8 (EC P-256)")
    return private_key


class AppleSignInClient(AppleSignInGateway):
    def __init__(
        self,
        *,
        client_ids: Iterable[str],
        team_id: str = "",
        key_id: str = "",
        private_key_pem: str = "",
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 10.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._audiences = [client_id for client_id in client_ids if client_id]
        if not self._audiences:
            raise ValueError("AppleSignInClient necesita al menos un client ID")
        self._team_id = team_id
        self._key_id = key_id
        self._private_key = (
            load_apple_private_key(private_key_pem) if private_key_pem else None
        )
        self._transport = transport
        self._timeout = timeout
        self._keys = JwksCache(KEYS_URL, transport=transport, clock=clock)

    @property
    def can_exchange_codes(self) -> bool:
        return bool(self._private_key and self._team_id and self._key_id)

    async def verify(
        self, identity_token: str, *, nonce: str | None
    ) -> ProviderIdentity:
        claims = await decode_provider_jwt(
            identity_token,
            provider=_PROVIDER,
            keys=self._keys,
            audiences=self._audiences,
            issuers=(ISSUER,),
            required=("exp", "iat", "iss", "aud", "sub"),
        )
        check_nonce(claims, nonce, provider=_PROVIDER)
        email = claims.get("email")
        verified = isinstance(email, str) and bool(email)
        verified = verified and is_true(claims.get("email_verified", True))
        private = is_true(claims.get("is_private_email")) or (
            verified and str(email).lower().endswith("@" + PRIVATE_RELAY_DOMAIN)
        )
        return ProviderIdentity(
            provider=IdentityProvider.APPLE,
            subject=str(claims["sub"]),
            audience=str(claims["aud"]),
            expires_at=datetime.fromtimestamp(int(claims["exp"]), UTC),
            email=str(email) if verified else None,
            private_email=private,
        )

    async def notification(self, payload: str) -> AppleNotification:
        """Los avisos van firmados como los identity tokens; `events` es un JSON en texto
        (https://developer.apple.com/documentation/sign_in_with_apple/processing-changes-for-sign-in-with-apple-accounts)."""
        claims = await decode_provider_jwt(
            payload,
            provider=_PROVIDER,
            keys=self._keys,
            audiences=self._audiences,
            issuers=(ISSUER,),
            required=("iat", "iss", "aud", "events"),
        )
        events = claims["events"]
        try:
            event = json.loads(events) if isinstance(events, str) else events
        except ValueError:
            raise InvalidProviderTokenError(_PROVIDER, "malformed") from None
        if not isinstance(event, dict):
            raise InvalidProviderTokenError(_PROVIDER, "malformed")
        kind, subject = event.get("type"), event.get("sub")
        if not isinstance(kind, str) or not isinstance(subject, str) or not subject:
            raise InvalidProviderTokenError(_PROVIDER, "malformed")
        event_time = event.get("event_time")
        jti = claims.get("jti")
        return AppleNotification(
            event=kind,
            subject=subject,
            notification_id=jti if isinstance(jti, str) and jti else None,
            event_time=_from_epoch(event_time),
        )

    async def exchange_code(
        self, authorization_code: str, *, client_id: str
    ) -> AppleTokens | None:
        response = await self._post(
            TOKEN_URL,
            client_id,
            {"code": authorization_code, "grant_type": "authorization_code"},
        )
        if response.status_code == httpx.codes.BAD_REQUEST:
            return None
        try:
            body = response.json()
        except ValueError:
            raise IdentityProviderUnavailableError(_PROVIDER) from None
        token = body.get("refresh_token") if isinstance(body, dict) else None
        if not isinstance(token, str) or not token:
            return None
        return AppleTokens(
            refresh_token=token,
            client_id=client_id,
            subject=_unverified_subject(body.get("id_token")),
        )

    async def revoke(self, refresh_token: str, *, client_id: str) -> None:
        response = await self._post(
            REVOKE_URL,
            client_id,
            {"token": refresh_token, "token_type_hint": "refresh_token"},
        )
        if response.status_code == httpx.codes.BAD_REQUEST:
            # Ya no valía (revocado desde Ajustes del iPhone, por ejemplo): nada que quitar.
            logger.info("Apple refresh token was already revoked")

    async def _post(
        self, url: str, client_id: str, fields: dict[str, str]
    ) -> httpx.Response:
        data = {
            "client_id": client_id,
            "client_secret": self.client_secret(client_id),
            **fields,
        }
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, transport=self._transport
            ) as client:
                response = await client.post(url, data=data)
        except httpx.HTTPError as error:
            raise IdentityProviderUnavailableError(_PROVIDER) from error
        if response.status_code not in (httpx.codes.OK, httpx.codes.BAD_REQUEST):
            logger.warning(
                "Apple answered an unexpected status",
                extra={"url": url, "status": response.status_code},
            )
            raise IdentityProviderUnavailableError(_PROVIDER)
        return response

    def client_secret(self, client_id: str) -> str:
        private_key = self._private_key
        if private_key is None or not self.can_exchange_codes:
            raise RuntimeError("Falta APPLE_TEAM_ID, APPLE_KEY_ID o APPLE_PRIVATE_KEY")
        now = datetime.now(UTC)
        claims = {
            "iss": self._team_id,
            "iat": now,
            "exp": now + CLIENT_SECRET_TTL,
            "aud": ISSUER,
            "sub": client_id,
        }
        return jwt.encode(
            claims, private_key, algorithm="ES256", headers={"kid": self._key_id}
        )


def _unverified_subject(id_token: Any) -> str | None:
    """`sub` del id_token que Apple devuelve en el canje. Llega directo de Apple por TLS y
    autenticado con nuestro client secret: no hace falta volver a comprobar la firma."""
    if not isinstance(id_token, str) or not id_token:
        return None
    try:
        claims = jwt.decode(id_token, options={"verify_signature": False})
    except jwt.PyJWTError:
        return None
    subject = claims.get("sub")
    return subject if isinstance(subject, str) and subject else None


def _from_epoch(value: Any) -> datetime | None:
    if not isinstance(value, int | float):
        return None
    # Apple manda `event_time` en milisegundos.
    seconds = value / 1000 if value > 10**11 else value
    return datetime.fromtimestamp(seconds, UTC)
