"""Google y Apple falsos para tests: claves RSA y .p8 generadas en cada ejecución, JWKS servido
con `httpx.MockTransport` y endpoints de Apple simulados. Nunca hay red.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs

import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from jwt.algorithms import RSAAlgorithm

from infrastructure.security import apple_sign_in, google_id_tokens
from infrastructure.security.apple_sign_in import AppleSignInClient
from infrastructure.security.google_id_tokens import GoogleIdTokenVerifier

GOOGLE_WEB_CLIENT = "web-123.apps.googleusercontent.com"
GOOGLE_IOS_CLIENT = "ios-456.apps.googleusercontent.com"
GOOGLE_CLIENT_IDS = [GOOGLE_WEB_CLIENT, GOOGLE_IOS_CLIENT]
APPLE_BUNDLE_ID = "app.lunance.ios"
APPLE_SERVICES_ID = "app.lunance.web"
APPLE_CLIENT_IDS = [APPLE_BUNDLE_ID, APPLE_SERVICES_ID]
APPLE_TEAM_ID = "TEAM123456"
APPLE_KEY_ID = "KEY1234567"
NONCE = "nonce-en-claro-0123456789"
ENCRYPTION_SECRET = "clave-de-cifrado-de-prueba-0123456789-abcdef"


def rsa_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def p8_pem() -> tuple[str, ec.EllipticCurvePrivateKey]:
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    return pem, key


def jwk(key: rsa.RSAPrivateKey, kid: str) -> dict[str, Any]:
    entry = json.loads(RSAAlgorithm.to_jwk(key.public_key()))
    return {**entry, "kid": kid, "alg": "RS256", "use": "sig"}


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


@dataclass
class FakeProvider:
    """Un proveedor con sus claves publicadas. `keys` se puede rotar en mitad del test."""

    issuer: str
    keys_url: str
    keys: dict[str, rsa.RSAPrivateKey] = field(default_factory=dict)
    cache_control: str = "public, max-age=3600"
    key_fetches: int = 0
    keys_down: bool = False

    def __post_init__(self) -> None:
        if not self.keys:
            self.keys = {"key-1": rsa_key()}

    def jwks_response(self) -> httpx.Response:
        self.key_fetches += 1
        if self.keys_down:
            return httpx.Response(503)
        return httpx.Response(
            200,
            json={"keys": [jwk(key, kid) for kid, key in self.keys.items()]},
            headers={"Cache-Control": self.cache_control},
        )

    def sign(
        self,
        claims: dict[str, Any],
        *,
        kid: str = "key-1",
        key: rsa.RSAPrivateKey | None = None,
        algorithm: str = "RS256",
    ) -> str:
        signing_key: Any = key or self.keys[kid]
        if algorithm.startswith("HS"):
            signing_key = "secreto-compartido-de-al-menos-32-bytes!"
        return jwt.encode(claims, signing_key, algorithm=algorithm, headers={"kid": kid})


def _claims(defaults: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = {**defaults, **overrides}
    return {name: value for name, value in merged.items() if value is not None}


@dataclass
class FakeGoogle(FakeProvider):
    issuer: str = "https://accounts.google.com"
    keys_url: str = google_id_tokens.CERTS_URL

    def id_token(self, **overrides: Any) -> str:
        """Token válido para el cliente web; `campo=None` lo quita."""
        now = datetime.now(UTC)
        sub = overrides.pop("sub", None) or str(uuid.uuid4().int)[:21]
        kid = overrides.pop("kid", "key-1")
        key = overrides.pop("key", None)
        algorithm = overrides.pop("algorithm", "RS256")
        claims = _claims(
            {
                "iss": self.issuer,
                "aud": GOOGLE_WEB_CLIENT,
                "azp": GOOGLE_WEB_CLIENT,
                "sub": sub,
                "email": f"user{sub[-6:]}@gmail.com",
                "email_verified": True,
                "name": "Ana López",
                "iat": now,
                "exp": now + timedelta(hours=1),
                "jti": uuid.uuid4().hex,
            },
            overrides,
        )
        return self.sign(claims, kid=kid, key=key, algorithm=algorithm)


@dataclass
class FakeApple(FakeProvider):
    issuer: str = apple_sign_in.ISSUER
    keys_url: str = apple_sign_in.KEYS_URL
    # Respuesta del canje: 200 con refresh token, 400 (código rechazado) o 500 (caído).
    token_status: int = 200
    token_subject: str | None = None
    revoked: list[str] = field(default_factory=list)
    requests: list[httpx.Request] = field(default_factory=list)

    def identity_token(self, **overrides: Any) -> str:
        now = datetime.now(UTC)
        sub = overrides.pop("sub", None) or f"000123.{uuid.uuid4().hex}.0042"
        kid = overrides.pop("kid", "key-1")
        claims = _claims(
            {
                "iss": self.issuer,
                "aud": APPLE_BUNDLE_ID,
                "sub": sub,
                "email": f"{uuid.uuid4().hex[:10]}@privaterelay.appleid.com",
                "email_verified": "true",
                "is_private_email": "true",
                "nonce": sha256(NONCE),
                "iat": now,
                "exp": now + timedelta(minutes=10),
            },
            overrides,
        )
        return self.sign(claims, kid=kid)

    def notification(self, event: str, sub: str, **overrides: Any) -> str:
        now = datetime.now(UTC)
        events = {"type": event, "sub": sub, "event_time": int(now.timestamp() * 1000)}
        claims = _claims(
            {
                "iss": self.issuer,
                "aud": APPLE_BUNDLE_ID,
                "iat": now,
                "jti": uuid.uuid4().hex,
                "events": json.dumps(events),
            },
            overrides,
        )
        return self.sign(claims)

    def token_response(self, request: httpx.Request) -> httpx.Response:
        if self.token_status != 200:
            return httpx.Response(self.token_status, json={"error": "invalid_grant"})
        form = parse_qs(request.content.decode())
        refresh = f"r{uuid.uuid4().hex}.0.abcd.{form['code'][0]}"
        body: dict[str, Any] = {
            "access_token": "a" + uuid.uuid4().hex,
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": refresh,
        }
        if self.token_subject:
            body["id_token"] = jwt.encode(
                {"sub": self.token_subject}, "x" * 32, algorithm="HS256"
            )
        return httpx.Response(200, json=body)

    def revoke_response(self, request: httpx.Request) -> httpx.Response:
        form = parse_qs(request.content.decode())
        self.revoked.append(form["token"][0])
        return httpx.Response(200)


def transport(*providers: FakeProvider) -> httpx.MockTransport:
    """Un solo transporte para todos los proveedores: cualquier otra URL falla el test."""

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        for provider in providers:
            if url == provider.keys_url:
                return provider.jwks_response()
            if isinstance(provider, FakeApple):
                provider.requests.append(request)
                if url == apple_sign_in.TOKEN_URL:
                    return provider.token_response(request)
                if url == apple_sign_in.REVOKE_URL:
                    return provider.revoke_response(request)
        raise AssertionError(f"petición inesperada a {url}")

    return httpx.MockTransport(handler)


class Clock:
    """Reloj monótono controlable para la caché de JWKS."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def google_verifier(google: FakeGoogle, clock: Clock | None = None) -> GoogleIdTokenVerifier:
    return GoogleIdTokenVerifier(
        client_ids=GOOGLE_CLIENT_IDS,
        transport=transport(google),
        clock=clock or Clock(),
    )


def apple_client(
    apple: FakeApple, *, with_key: bool = True, clock: Clock | None = None
) -> tuple[AppleSignInClient, ec.EllipticCurvePrivateKey | None]:
    pem, key = p8_pem() if with_key else ("", None)
    client = AppleSignInClient(
        client_ids=APPLE_CLIENT_IDS,
        team_id=APPLE_TEAM_ID if with_key else "",
        key_id=APPLE_KEY_ID if with_key else "",
        private_key_pem=pem,
        transport=transport(apple),
        clock=clock or Clock(),
    )
    return client, key
