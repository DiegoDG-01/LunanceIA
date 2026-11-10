from datetime import UTC, datetime, timedelta

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from application.interfaces.auth_service import (
    AccessClaims,
    AccessTokenIssuer,
    IssuedAccessToken,
)
from shared.exceptions.application import JWTValidationError

_ALGORITHM = "EdDSA"


class EdDSATokenIssuer(AccessTokenIssuer):
    """Access token JWT firmado con Ed25519: `iss`, `aud`, `sub` (uuid del usuario), `sid`
    (uuid de la sesión), `iat` y `exp`."""

    def __init__(
        self,
        *,
        private_key_pem: str,
        public_key_pem: str,
        issuer: str,
        audience: str,
        ttl_seconds: int,
        leeway_seconds: int = 10,
    ) -> None:
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(), password=None
        )
        public_key = serialization.load_pem_public_key(public_key_pem.encode())
        if not isinstance(private_key, Ed25519PrivateKey) or not isinstance(
            public_key, Ed25519PublicKey
        ):
            raise TypeError("Las claves del JWT deben ser Ed25519.")
        self._private_key = private_key
        self._public_key = public_key
        self._issuer = issuer
        self._audience = audience
        self._ttl_seconds = ttl_seconds
        self._leeway = leeway_seconds

    @property
    def ttl_seconds(self) -> int:
        return self._ttl_seconds

    @property
    def leeway_seconds(self) -> int:
        return self._leeway

    def issue(self, *, user_uuid: str, session_uuid: str) -> IssuedAccessToken:
        now = datetime.now(UTC)
        payload = {
            "iss": self._issuer,
            "aud": self._audience,
            "sub": user_uuid,
            "sid": session_uuid,
            "iat": now,
            "exp": now + timedelta(seconds=self._ttl_seconds),
        }
        token = jwt.encode(payload, self._private_key, algorithm=_ALGORITHM)
        return IssuedAccessToken(token=token, expires_in=self._ttl_seconds)

    def verify(self, token: str) -> AccessClaims:
        try:
            payload = jwt.decode(
                token,
                self._public_key,
                algorithms=[_ALGORITHM],
                audience=self._audience,
                issuer=self._issuer,
                leeway=self._leeway,
                options={"require": ["iss", "aud", "exp", "iat", "sub", "sid"]},
            )
        except jwt.ExpiredSignatureError as error:
            raise JWTValidationError("Token expired") from error
        except jwt.PyJWTError as error:
            raise JWTValidationError("Invalid token") from error

        user_uuid, session_uuid = payload["sub"], payload["sid"]
        if not isinstance(user_uuid, str) or not isinstance(session_uuid, str):
            raise JWTValidationError("Invalid token")
        return AccessClaims(
            user_uuid=user_uuid,
            session_uuid=session_uuid,
            expires_at=datetime.fromtimestamp(payload["exp"], UTC),
        )
