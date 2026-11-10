"""Helpers de autenticación para tests: claves Ed25519 nuevas, Argon2 rápido y Redis caído."""

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from infrastructure.security.jwt_tokens import EdDSATokenIssuer
from infrastructure.security.passwords import Argon2PasswordHasher


def make_issuer(ttl_seconds: int = 600) -> EdDSATokenIssuer:
    key = Ed25519PrivateKey.generate()
    return EdDSATokenIssuer(
        private_key_pem=key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode(),
        public_key_pem=key.public_key()
        .public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        .decode(),
        issuer="lunance",
        audience="lunance-api",
        ttl_seconds=ttl_seconds,
    )


def fast_hasher() -> Argon2PasswordHasher:
    return Argon2PasswordHasher(time_cost=1, memory_cost_kib=8, parallelism=1)


class BrokenRedis:
    """Redis caído: cualquier operación falla con ConnectionError."""

    def __getattr__(self, name):
        from redis.exceptions import ConnectionError as RedisConnectionError

        def _fail(*args, **kwargs):
            raise RedisConnectionError("redis down")

        return _fail
