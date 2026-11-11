"""Verificación de ID tokens de Google y Apple, caché de JWKS, canje y revocación con Apple,
cifrado del refresh token y tokens de un solo uso. Claves generadas aquí; sin red."""

from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs

import jwt
import pytest
from fakeredis import FakeAsyncRedis

from application.auth.services.external_accounts import owner_confirmed, username_base
from application.interfaces.identity_providers import (
    AppleNotification,
    IdentityProvider,
    ProviderIdentity,
)
from infrastructure.cache.provider_tokens import RedisUsedProviderTokens
from infrastructure.config.settings import Settings
from infrastructure.security.apple_sign_in import ISSUER, TOKEN_URL
from infrastructure.security.secret_cipher import AesGcmSecretCipher
from shared.exceptions.application import (
    IdentityProviderUnavailableError,
    InvalidProviderTokenError,
    ServiceTemporarilyUnavailableError,
)
from tests.auth_helpers import BrokenRedis
from tests.identity_providers import (
    APPLE_BUNDLE_ID,
    APPLE_KEY_ID,
    APPLE_SERVICES_ID,
    APPLE_TEAM_ID,
    ENCRYPTION_SECRET,
    GOOGLE_IOS_CLIENT,
    NONCE,
    Clock,
    FakeApple,
    FakeGoogle,
    apple_client,
    google_verifier,
    p8_pem,
    rsa_key,
    sha256,
)

async def _reason(coroutine) -> str:
    with pytest.raises(InvalidProviderTokenError) as caught:
        await coroutine
    return caught.value.reason


class TestGoogleIdTokens:
    async def test_valid_token(self):
        google = FakeGoogle()
        verifier = google_verifier(google)

        identity = await verifier.verify(
            google.id_token(sub="1234567890", email="Ana@Gmail.com", hd=None),
            nonce=None,
        )

        assert identity.provider is IdentityProvider.GOOGLE
        assert identity.subject == "1234567890"
        assert identity.email == "Ana@Gmail.com"
        assert identity.name == "Ana López"
        assert identity.hosted_domain is None

    async def test_accepts_every_configured_audience(self):
        google = FakeGoogle()

        identity = await google_verifier(google).verify(
            google.id_token(aud=GOOGLE_IOS_CLIENT), nonce=None
        )

        assert identity.audience == GOOGLE_IOS_CLIENT

    @pytest.mark.parametrize(
        ("claims", "reason"),
        [
            ({"aud": "someone-else.apps.googleusercontent.com"}, "audience"),
            ({"iss": "https://evil.example.com"}, "issuer"),
            ({"exp": datetime.now(UTC) - timedelta(minutes=5)}, "expired"),
            ({"iat": datetime.now(UTC) + timedelta(minutes=10)}, "issued_in_future"),
            ({"sub": None, "email": "x@gmail.com"}, "missing_claim"),
            ({"email_verified": False}, "email_not_verified"),
            ({"email_verified": "false"}, "email_not_verified"),
            ({"email": None}, "email_missing"),
        ],
        ids=[
            "audience",
            "issuer",
            "expired",
            "iat-future",
            "no-sub",
            "unverified",
            "unverified-text",
            "no-email",
        ],
    )
    async def test_rejects_invalid_claims(self, claims, reason):
        google = FakeGoogle()
        token = google.id_token(**claims)
        if claims.get("sub", "x") is None:
            # FakeGoogle siempre pone sub: se vuelve a firmar sin él.
            payload = jwt.decode(token, options={"verify_signature": False})
            payload.pop("sub")
            token = google.sign(payload)

        assert await _reason(google_verifier(google).verify(token, nonce=None)) == reason

    async def test_small_leeway_accepts_a_token_that_just_expired(self):
        google = FakeGoogle()
        token = google.id_token(exp=datetime.now(UTC) - timedelta(seconds=3))

        assert await google_verifier(google).verify(token, nonce=None)

    async def test_rejects_a_signature_from_another_key(self):
        google = FakeGoogle()
        forged = google.id_token(key=rsa_key())

        assert await _reason(google_verifier(google).verify(forged, nonce=None)) == (
            "signature"
        )

    @pytest.mark.parametrize("algorithm", ["HS256", "none"])
    async def test_rejects_other_algorithms(self, algorithm):
        google = FakeGoogle()
        now = datetime.now(UTC)
        claims = {"iss": google.issuer, "sub": "1", "iat": now, "exp": now}
        token = (
            jwt.encode(claims, "", algorithm="none", headers={"kid": "key-1"})
            if algorithm == "none"
            else google.sign(claims, algorithm="HS256")
        )

        assert await _reason(google_verifier(google).verify(token, nonce=None)) == (
            "algorithm"
        )

    async def test_rejects_garbage(self):
        google = FakeGoogle()
        verifier = google_verifier(google)

        assert await _reason(verifier.verify("no-es-un-jwt", nonce=None)) == "malformed"
        assert await _reason(verifier.verify("x" * 9000, nonce=None)) == "malformed"
        assert google.key_fetches == 0

    async def test_nonce_must_match_its_hash(self):
        google = FakeGoogle()
        verifier = google_verifier(google)

        ok = await verifier.verify(google.id_token(nonce=sha256(NONCE)), nonce=NONCE)
        assert ok.subject
        assert (
            await _reason(
                verifier.verify(google.id_token(nonce=sha256(NONCE)), nonce="otro")
            )
            == "nonce"
        )
        assert (
            await _reason(verifier.verify(google.id_token(nonce=sha256(NONCE)), nonce=None))
            == "nonce"
        )
        assert (
            await _reason(verifier.verify(google.id_token(), nonce=NONCE)) == "nonce"
        )
        # El valor en claro dentro del token no vale: debe ser su hash.
        assert (
            await _reason(verifier.verify(google.id_token(nonce=NONCE), nonce=NONCE))
            == "nonce"
        )

    async def test_workspace_domain_is_lowercased(self):
        google = FakeGoogle()

        identity = await google_verifier(google).verify(
            google.id_token(email="ana@Empresa.com", hd="Empresa.com"), nonce=None
        )

        assert identity.hosted_domain == "empresa.com"


class TestJwksCache:
    async def test_keys_are_cached_for_their_max_age(self):
        google, clock = FakeGoogle(cache_control="public, max-age=600"), Clock()
        verifier = google_verifier(google, clock)

        await verifier.verify(google.id_token(), nonce=None)
        clock.now += 599
        await verifier.verify(google.id_token(), nonce=None)
        assert google.key_fetches == 1

        clock.now += 2
        await verifier.verify(google.id_token(), nonce=None)
        assert google.key_fetches == 2

    async def test_unknown_kid_refetches_after_rotation(self):
        google, clock = FakeGoogle(), Clock()
        verifier = google_verifier(google, clock)
        await verifier.verify(google.id_token(), nonce=None)

        google.keys["key-2"] = rsa_key()
        clock.now += 61
        identity = await verifier.verify(google.id_token(kid="key-2"), nonce=None)

        assert identity.subject
        assert google.key_fetches == 2

    async def test_unknown_kid_refetch_is_rate_limited(self):
        google, clock = FakeGoogle(), Clock()
        verifier = google_verifier(google, clock)
        await verifier.verify(google.id_token(), nonce=None)
        stranger = google.sign(
            {"sub": "1"}, kid="no-existe", key=rsa_key()
        )

        for _ in range(5):
            assert (
                await _reason(verifier.verify(stranger, nonce=None)) == "unknown_key"
            )
            clock.now += 10

        # Una descarga inicial y, como mucho, una más por minuto.
        assert google.key_fetches == 1
        clock.now += 20
        await _reason(verifier.verify(stranger, nonce=None))
        assert google.key_fetches == 2

    async def test_provider_down_without_cached_keys_is_unavailable(self):
        google = FakeGoogle(keys_down=True)

        with pytest.raises(IdentityProviderUnavailableError):
            await google_verifier(google).verify(google.id_token(), nonce=None)

    async def test_keeps_cached_keys_when_a_refresh_fails(self):
        google, clock = FakeGoogle(), Clock()
        verifier = google_verifier(google, clock)
        await verifier.verify(google.id_token(), nonce=None)

        google.keys_down = True
        clock.now += 61
        unknown = google.sign({"sub": "1"}, kid="key-9", key=rsa_key())
        assert await _reason(verifier.verify(unknown, nonce=None)) == "unknown_key"
        assert await verifier.verify(google.id_token(), nonce=None)


class TestAppleSignIn:
    async def test_valid_identity_token_with_private_relay(self):
        apple = FakeApple()
        client, _ = apple_client(apple)

        identity = await client.verify(apple.identity_token(sub="001.abc.002"), nonce=NONCE)

        assert identity.provider is IdentityProvider.APPLE
        assert identity.subject == "001.abc.002"
        assert identity.audience == APPLE_BUNDLE_ID
        assert identity.private_email is True
        assert identity.email and identity.email.endswith("@privaterelay.appleid.com")

    async def test_services_id_is_an_accepted_audience(self):
        apple = FakeApple()
        client, _ = apple_client(apple)

        identity = await client.verify(
            apple.identity_token(aud=APPLE_SERVICES_ID), nonce=NONCE
        )

        assert identity.audience == APPLE_SERVICES_ID

    @pytest.mark.parametrize(
        ("claims", "nonce", "reason"),
        [
            ({"aud": "com.someone.else"}, NONCE, "audience"),
            ({"iss": "https://accounts.google.com"}, NONCE, "issuer"),
            ({"exp": datetime.now(UTC) - timedelta(minutes=1)}, NONCE, "expired"),
            ({}, "otro-nonce", "nonce"),
            ({}, None, "nonce"),
        ],
        ids=["audience", "issuer", "expired", "other-nonce", "missing-nonce"],
    )
    async def test_rejects_invalid_tokens(self, claims, nonce, reason):
        apple = FakeApple()
        client, _ = apple_client(apple)

        assert (
            await _reason(client.verify(apple.identity_token(**claims), nonce=nonce))
            == reason
        )

    async def test_unverified_or_missing_email_is_dropped(self):
        apple = FakeApple()
        client, _ = apple_client(apple)

        without = await client.verify(apple.identity_token(email=None), nonce=NONCE)
        unverified = await client.verify(
            apple.identity_token(email_verified="false"), nonce=NONCE
        )

        assert without.email is None
        assert unverified.email is None

    async def test_exchange_code_signs_an_es256_client_secret(self):
        apple = FakeApple(token_subject="001.abc.002")
        client, key = apple_client(apple)

        tokens = await client.exchange_code("code-1", client_id=APPLE_SERVICES_ID)

        assert tokens is not None
        assert tokens.client_id == APPLE_SERVICES_ID
        assert tokens.subject == "001.abc.002"
        assert tokens.refresh_token.endswith(".code-1")
        [request] = [r for r in apple.requests if str(r.url) == TOKEN_URL]
        form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
        assert form["grant_type"] == "authorization_code"
        assert form["client_id"] == APPLE_SERVICES_ID
        assert key is not None
        secret = jwt.decode(
            form["client_secret"],
            key.public_key(),
            algorithms=["ES256"],
            audience=ISSUER,
        )
        assert secret["iss"] == APPLE_TEAM_ID
        assert secret["sub"] == APPLE_SERVICES_ID
        assert jwt.get_unverified_header(form["client_secret"])["kid"] == APPLE_KEY_ID

    async def test_rejected_code_returns_none_and_errors_are_unavailable(self):
        rejected = FakeApple(token_status=400)
        client, _ = apple_client(rejected)
        assert await client.exchange_code("used", client_id=APPLE_BUNDLE_ID) is None

        down = FakeApple(token_status=500)
        client, _ = apple_client(down)
        with pytest.raises(IdentityProviderUnavailableError):
            await client.exchange_code("code", client_id=APPLE_BUNDLE_ID)

    async def test_without_p8_key_codes_cannot_be_exchanged(self):
        client, _ = apple_client(FakeApple(), with_key=False)

        assert client.can_exchange_codes is False

    async def test_revoke_posts_the_refresh_token(self):
        apple = FakeApple()
        client, _ = apple_client(apple)

        await client.revoke("r-token", client_id=APPLE_BUNDLE_ID)

        assert apple.revoked == ["r-token"]

    async def test_reads_notifications(self):
        apple = FakeApple()
        client, _ = apple_client(apple)

        notification = await client.notification(
            apple.notification("consent-revoked", "001.abc.002", jti="n-1")
        )

        assert isinstance(notification, AppleNotification)
        assert (notification.event, notification.subject) == (
            "consent-revoked",
            "001.abc.002",
        )
        assert notification.notification_id == "n-1"
        assert notification.event_time is not None

    async def test_rejects_notifications_for_another_app_or_forged(self):
        apple = FakeApple()
        client, _ = apple_client(apple)

        other_app = apple.notification("account-delete", "001", aud="com.other")
        forged = apple.sign(
            jwt.decode(other_app, options={"verify_signature": False})
            | {"aud": APPLE_BUNDLE_ID},
            key=rsa_key(),
        )

        assert await _reason(client.notification(other_app)) == "audience"
        assert await _reason(client.notification(forged)) == "signature"
        assert await _reason(client.notification(apple.sign({"iss": ISSUER, "aud": APPLE_BUNDLE_ID, "iat": datetime.now(UTC), "events": "no-json"}))) == "malformed"


class TestSecretCipher:
    def test_round_trip_and_context_binding(self):
        cipher = AesGcmSecretCipher(ENCRYPTION_SECRET, purpose="apple-refresh-token")

        sealed = cipher.encrypt("r-secret", context="users:1")

        assert sealed.startswith("v1.") and "r-secret" not in sealed
        assert cipher.decrypt(sealed, context="users:1") == "r-secret"
        assert cipher.encrypt("r-secret", context="users:1") != sealed
        with pytest.raises(ValueError):
            cipher.decrypt(sealed, context="users:2")

    def test_tampering_or_another_key_fails(self):
        cipher = AesGcmSecretCipher(ENCRYPTION_SECRET, purpose="apple-refresh-token")
        other = AesGcmSecretCipher("x" * 40, purpose="apple-refresh-token")
        sealed = cipher.encrypt("r-secret", context="users:1")
        tampered = sealed[:-2] + ("A" if sealed[-2] != "A" else "B") + sealed[-1]

        for bad in (tampered, "v2." + sealed[3:], "basura"):
            with pytest.raises(ValueError):
                cipher.decrypt(bad, context="users:1")
        with pytest.raises(ValueError):
            other.decrypt(sealed, context="users:1")

    def test_rejects_short_secrets(self):
        with pytest.raises(ValueError):
            AesGcmSecretCipher("corta", purpose="x")


class TestUsedProviderTokens:
    async def test_each_token_is_accepted_once_until_it_expires(self):
        redis = FakeAsyncRedis(decode_responses=True)
        now = datetime(2026, 11, 10, 12, tzinfo=UTC)
        used = RedisUsedProviderTokens(lambda: redis, now=lambda: now)

        assert await used.claim("token-a", expires_at=now + timedelta(minutes=10))
        assert not await used.claim("token-a", expires_at=now + timedelta(minutes=10))
        assert await used.claim("token-b", expires_at=now + timedelta(minutes=10))
        keys = [str(k) for k in await redis.keys("provider_token:*")]
        [key] = [k for k in keys if k.endswith(sha256("token-a"))]
        assert 600 < await redis.ttl(key) <= 720
        assert "token-a" not in key

    async def test_redis_down_fails_closed(self):
        used = RedisUsedProviderTokens(lambda: BrokenRedis())  # type: ignore[arg-type]

        with pytest.raises(ServiceTemporarilyUnavailableError):
            await used.claim("token", expires_at=datetime.now(UTC))


def _identity(provider: IdentityProvider, **fields) -> ProviderIdentity:
    return ProviderIdentity(
        provider=provider,
        subject="1",
        audience="aud",
        expires_at=datetime.now(UTC),
        **fields,
    )


class TestStableMailboxes:
    @pytest.mark.parametrize(
        ("provider", "email", "hd", "expected"),
        [
            (IdentityProvider.GOOGLE, "ana@gmail.com", None, True),
            (IdentityProvider.GOOGLE, "ana@googlemail.com", None, True),
            (IdentityProvider.GOOGLE, "ana@empresa.com", "empresa.com", True),
            (IdentityProvider.GOOGLE, "ana@empresa.com", None, False),
            (IdentityProvider.GOOGLE, "ana@empresa.com", "otra.com", False),
            (IdentityProvider.GOOGLE, "ana@icloud.com", None, False),
            (IdentityProvider.GOOGLE, "ana@privaterelay.appleid.com", None, False),
            (IdentityProvider.APPLE, "ana@icloud.com", None, True),
            (IdentityProvider.APPLE, "ana@me.com", None, True),
            (IdentityProvider.APPLE, "ana@mac.com", None, True),
            (IdentityProvider.APPLE, "x1@privaterelay.appleid.com", None, True),
            (IdentityProvider.APPLE, "ana@gmail.com", None, False),
            (IdentityProvider.APPLE, "ana@empresa.com", "empresa.com", False),
        ],
    )
    def test_owner_confirmed(self, provider, email, hd, expected):
        identity = _identity(provider, email=email, hosted_domain=hd)

        assert owner_confirmed(identity, email) is expected

    @pytest.mark.parametrize(
        ("name", "email", "expected"),
        [
            ("María José", None, "mariajose"),
            ("  Ño Ñandú 2 ", None, "nonandu2"),
            ("123 Ana", None, "ana"),
            ("李", "diego.dg@gmail.com", "diego.dg"),
            (None, "42@gmail.com", "usuario"),
            ("Un nombre larguísimo de verdad", None, "unnombrelarguisimode"),
        ],
    )
    def test_username_base(self, name, email, expected):
        assert username_base(name, email) == expected


class TestSettings:
    def _settings(self, **values) -> Settings:
        """Sin .env: solo lo que pasa el test (las claves del JWT vienen de conftest)."""
        values.setdefault("ENVIRONMENT", "DEV")
        values.setdefault("EMAIL_BACKEND", "memory")
        required = {
            "DB_NAME": "x",
            "DB_USER": "x",
            "DB_PASSWORD": "x",
            "AI_PROVIDER": "x",
            "AI_MODEL_ID": "x",
        }
        return Settings(_env_file=None, **(required | values))  # type: ignore[call-arg]

    def test_providers_are_off_by_default_and_lists_split_by_comma(self):
        assert self._settings().GOOGLE_CLIENT_IDS == []
        settings = self._settings(GOOGLE_CLIENT_IDS="a.apps, b.apps", APPLE_CLIENT_IDS="com.x")
        assert settings.GOOGLE_CLIENT_IDS == ["a.apps", "b.apps"]
        assert settings.APPLE_CLIENT_IDS == ["com.x"]

    def test_apple_signing_settings_go_together(self):
        with pytest.raises(ValueError, match="van juntos"):
            self._settings(APPLE_CLIENT_IDS="com.x", APPLE_TEAM_ID="T")

    def test_prod_with_apple_needs_the_p8_key(self):
        with pytest.raises(ValueError, match="En PROD"):
            self._settings(
                ENVIRONMENT="PROD",
                EMAIL_BACKEND="resend",
                RESEND_API_KEY="re_x",
                EMAIL_LINK_BASE_URL="https://lunance.app",
                APPLE_CLIENT_IDS="com.x",
            )

    def test_p8_key_is_validated_and_needs_the_encryption_key(self):
        pem, _ = p8_pem()
        base = {"APPLE_CLIENT_IDS": "com.x", "APPLE_TEAM_ID": "T", "APPLE_KEY_ID": "K"}
        with pytest.raises(ValueError, match="APPLE_TOKEN_ENCRYPTION_KEY"):
            self._settings(**base, APPLE_PRIVATE_KEY=pem)
        with pytest.raises(ValueError, match=".p8"):
            self._settings(**base, APPLE_PRIVATE_KEY="no-es-pem", APPLE_TOKEN_ENCRYPTION_KEY=ENCRYPTION_SECRET)
        settings = self._settings(
            **base,
            APPLE_PRIVATE_KEY=pem.replace("\n", "\\n"),
            APPLE_TOKEN_ENCRYPTION_KEY=ENCRYPTION_SECRET,
        )
        assert settings.APPLE_PRIVATE_KEY.get_secret_value() == pem

    def test_google_alone_needs_nothing_else_in_prod(self):
        settings = self._settings(
            ENVIRONMENT="PROD",
            EMAIL_BACKEND="resend",
            RESEND_API_KEY="re_x",
            EMAIL_LINK_BASE_URL="https://lunance.app",
            GOOGLE_CLIENT_IDS="a.apps",
        )
        assert settings.GOOGLE_CLIENT_IDS == ["a.apps"]
