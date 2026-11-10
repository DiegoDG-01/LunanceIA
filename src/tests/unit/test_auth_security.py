"""Primitivas de seguridad de la fase 1: JWT EdDSA, Argon2 + bcrypt heredado, refresh opaco y
la cabecera X-Lunance-Client."""

import time
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
import pytest
from fastapi.exceptions import RequestValidationError

from domain.entities.auth.session import Platform
from presentation.dependencies.client_deps import parse_client
from shared.exceptions.application import JWTValidationError
from shared.utils.tokens import (
    REFRESH_TOKEN_PREFIX,
    generate_token,
    hash_token,
    refresh_successor,
)
from tests.auth_helpers import fast_hasher, make_issuer

USER = "6f1c2d1e-8b6a-4c55-9f61-2b0b0c3b8d10"
SID = "a3b9d6f0-1c2e-4f5a-8b7c-9d0e1f2a3b4c"


@pytest.mark.unit
class TestEdDSATokenIssuer:
    def test_round_trip_carries_user_and_session(self):
        issuer = make_issuer()

        issued = issuer.issue(user_uuid=USER, session_uuid=SID)
        claims = issuer.verify(issued.token)

        assert issued.expires_in == 600
        assert claims.user_uuid == USER
        assert claims.session_uuid == SID
        payload = jwt.decode(issued.token, options={"verify_signature": False})
        assert payload["iss"] == "lunance"
        assert payload["aud"] == "lunance-api"
        assert set(payload) == {"iss", "aud", "sub", "sid", "iat", "exp"}
        assert payload["exp"] - payload["iat"] == 600
        assert jwt.get_unverified_header(issued.token)["alg"] == "EdDSA"

    def test_expired_token_is_rejected(self):
        issuer = make_issuer(ttl_seconds=-60)

        with pytest.raises(JWTValidationError, match="expired"):
            issuer.verify(issuer.issue(user_uuid=USER, session_uuid=SID).token)

    def test_token_from_other_key_is_rejected(self):
        token = make_issuer().issue(user_uuid=USER, session_uuid=SID).token

        with pytest.raises(JWTValidationError):
            make_issuer().verify(token)

    def test_hs256_token_is_rejected(self):
        now = int(time.time())
        forged = jwt.encode(
            {
                "iss": "lunance",
                "aud": "lunance-api",
                "sub": USER,
                "sid": SID,
                "iat": now,
                "exp": now + 600,
            },
            "x" * 32,
            algorithm="HS256",
        )

        with pytest.raises(JWTValidationError):
            make_issuer().verify(forged)

    def test_wrong_audience_is_rejected(self):
        issuer = make_issuer()
        payload = jwt.decode(
            issuer.issue(user_uuid=USER, session_uuid=SID).token,
            options={"verify_signature": False},
        )
        payload["aud"] = "someone-else"
        token = jwt.encode(payload, issuer._private_key, algorithm="EdDSA")

        with pytest.raises(JWTValidationError):
            issuer.verify(token)

    def test_token_without_sid_is_rejected(self):
        issuer = make_issuer()
        now = datetime.now(UTC)
        token = jwt.encode(
            {
                "iss": "lunance",
                "aud": "lunance-api",
                "sub": USER,
                "iat": now,
                "exp": now + timedelta(minutes=10),
            },
            issuer._private_key,
            algorithm="EdDSA",
        )

        with pytest.raises(JWTValidationError):
            issuer.verify(token)

    def test_non_ed25519_keys_are_refused(self):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec

        key = ec.generate_private_key(ec.SECP256R1())
        with pytest.raises(TypeError):
            type(make_issuer())(
                private_key_pem=key.private_bytes(
                    serialization.Encoding.PEM,
                    serialization.PrivateFormat.PKCS8,
                    serialization.NoEncryption(),
                ).decode(),
                public_key_pem=key.public_key()
                .public_bytes(
                    serialization.Encoding.PEM,
                    serialization.PublicFormat.SubjectPublicKeyInfo,
                )
                .decode(),
                issuer="lunance",
                audience="lunance-api",
                ttl_seconds=600,
            )


@pytest.mark.unit
@pytest.mark.asyncio
class TestArgon2PasswordHasher:
    async def test_hashes_with_argon2id(self):
        hasher = fast_hasher()

        hashed = await hasher.hash("Password123!")

        assert hashed.startswith("$argon2id$")
        assert await hasher.verify("Password123!", hashed)
        assert not await hasher.verify("Password124!", hashed)
        assert not hasher.needs_rehash(hashed)

    async def test_verifies_legacy_bcrypt_and_flags_rehash(self):
        hasher = fast_hasher()
        legacy = bcrypt.hashpw(b"Password123!", bcrypt.gensalt(rounds=4)).decode()

        assert await hasher.verify("Password123!", legacy)
        assert not await hasher.verify("nope-nope", legacy)
        assert hasher.needs_rehash(legacy)

    async def test_stronger_parameters_flag_rehash(self):
        weak = await fast_hasher().hash("Password123!")

        assert type(fast_hasher())(time_cost=2, memory_cost_kib=8).needs_rehash(weak)

    async def test_garbage_hash_never_verifies(self):
        hasher = fast_hasher()

        assert not await hasher.verify("Password123!", "not-a-hash")
        assert not await hasher.verify("x" * 100, "$2b$04$" + "a" * 53)

    async def test_verify_dummy_does_not_raise(self):
        hasher = fast_hasher()

        await hasher.verify_dummy("whatever")
        await hasher.verify_dummy("whatever")


@pytest.mark.unit
class TestOpaqueRefreshTokens:
    def test_generated_token_has_prefix_and_256_bits(self):
        token = generate_token(REFRESH_TOKEN_PREFIX)

        assert token.startswith("rt_")
        assert len(token) - 3 >= 43  # 32 bytes en base64url
        assert generate_token(REFRESH_TOKEN_PREFIX) != token

    def test_hash_is_sha256_hex(self):
        assert len(hash_token("rt_abc")) == 64
        assert hash_token("rt_abc") == hash_token("rt_abc")

    def test_successor_is_deterministic_and_keyed(self):
        key, other = b"k" * 32, b"o" * 32

        successor = refresh_successor("rt_abc", key=key)

        assert successor.startswith("rt_")
        assert successor == refresh_successor("rt_abc", key=key)
        assert successor != refresh_successor("rt_abc", key=other)
        assert successor != refresh_successor("rt_abd", key=key)


@pytest.mark.unit
class TestClientHeader:
    @pytest.mark.parametrize(
        ("header", "platform"),
        [
            ("ios/1.4.0", Platform.IOS),
            ("android/2.0", Platform.ANDROID),
            ("web/2026.11", Platform.WEB),
            ("iOS/1.0", Platform.IOS),
            ("web", Platform.WEB),
        ],
    )
    def test_parses_platform(self, header, platform):
        assert parse_client(header) == (platform, header)

    @pytest.mark.parametrize("header", [None, "", "   "])
    def test_missing_header_is_web(self, header):
        assert parse_client(header) == (Platform.WEB, None)

    @pytest.mark.parametrize("header", ["windows/1.0", "ios-1.0", "ios/" + "1" * 60])
    def test_invalid_header_is_422(self, header):
        with pytest.raises(RequestValidationError):
            parse_client(header)
