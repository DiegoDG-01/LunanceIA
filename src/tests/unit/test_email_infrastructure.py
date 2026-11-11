"""Envío de correo (Resend, SMTP, memoria), plantillas, settings del correo y throttle del
login en Redis."""

import json
import logging
from datetime import timedelta

import httpx
import pytest
from fakeredis import FakeAsyncRedis
from pydantic import ValidationError

from application.auth.emails import (
    account_already_exists,
    app_link,
    describe_ttl,
    email_verification,
    password_reset,
)
from application.interfaces.email import EmailDeliveryError, OutgoingEmail
from infrastructure.cache.login_throttle import RedisLoginThrottle
from infrastructure.config.settings import Settings
from infrastructure.external_services.email.delivery import deliver
from infrastructure.external_services.email.factory import build_email_sender
from infrastructure.external_services.email.memory import InMemoryEmailSender
from infrastructure.external_services.email.resend import ResendEmailSender
from infrastructure.external_services.email.smtp import SmtpEmailSender
from shared.exceptions.application import ServiceTemporarilyUnavailableError
from shared.utils.emails import email_digest, normalize_email
from tests.auth_helpers import BrokenRedis

EMAIL = OutgoingEmail(
    to=["ana@example.com"],
    subject="Asunto",
    text="Hola",
    html="<p>Hola</p>",
    tag="verify-email",
)


def _settings(**overrides) -> Settings:
    base = {
        "JWT_PRIVATE_KEY": "k",
        "JWT_PUBLIC_KEY": "k",
        "REFRESH_ROTATION_KEY": "x" * 40,
        "DB_NAME": "db",
        "DB_USER": "u",
        "DB_PASSWORD": "p",
        "AI_PROVIDER": "p",
        "AI_MODEL_ID": "m",
        "ENVIRONMENT": "DEV",
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[call-arg]


@pytest.mark.unit
class TestEmailUtils:
    def test_normalize_email(self):
        assert normalize_email("  Ana.Perez@Example.COM ") == "ana.perez@example.com"

    def test_digest_does_not_contain_the_email(self):
        digest = email_digest("Ana@Example.com")
        assert digest == email_digest("ana@example.com")
        assert "ana" not in digest and len(digest) == 32


@pytest.mark.unit
class TestTemplates:
    def test_links_carry_the_token(self):
        assert (
            app_link("https://lunance.app/", "verify-email", "abc")
            == "https://lunance.app/verify-email?token=abc"
        )
        assert app_link("https://lunance.app", "login") == "https://lunance.app/login"

    @pytest.mark.parametrize(
        ("ttl", "text"),
        [
            (timedelta(hours=24), "1 día"),
            (timedelta(hours=1), "1 hora"),
            (timedelta(hours=3), "3 horas"),
            (timedelta(minutes=30), "30 minutos"),
        ],
    )
    def test_describe_ttl(self, ttl, text):
        assert describe_ttl(ttl) == text

    def test_html_escapes_user_values(self):
        email = email_verification(
            to="ana@example.com",
            username="<script>alert(1)</script>",
            link="https://lunance.app/verify-email?token=abc&x=1",
            ttl=timedelta(hours=24),
        )

        assert email.html is not None
        assert "<script>" not in email.html
        assert "&lt;script&gt;" in email.html
        assert "token=abc&amp;x=1" in email.html
        assert "https://lunance.app/verify-email?token=abc&x=1" in email.text
        assert "24 horas" not in email.text and "1 día" in email.text

    def test_existing_account_notice_has_no_token(self):
        email = account_already_exists(
            to="ana@example.com",
            login_link="https://lunance.app/login",
            forgot_link="https://lunance.app/forgot-password",
        )

        assert "token" not in email.text
        assert "forgot-password" in email.text

    def test_reset_mentions_single_use_and_expiry(self):
        email = password_reset(
            to="ana@example.com",
            username="ana",
            link="https://lunance.app/reset-password?token=t",
            ttl=timedelta(hours=1),
        )

        assert "1 hora" in email.text and "una vez" in email.text


@pytest.mark.unit
@pytest.mark.asyncio
class TestResendSender:
    async def test_posts_the_message_with_bearer_key(self):
        seen: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(200, json={"id": "email_1"})

        sender = ResendEmailSender(
            api_key="re_test",
            sender="Lunance <no-reply@lunance.app>",
            transport=httpx.MockTransport(handler),
        )

        await sender.send(EMAIL)

        [request] = seen
        assert str(request.url) == ResendEmailSender.ENDPOINT
        assert request.headers["Authorization"] == "Bearer re_test"
        payload = json.loads(request.content)
        assert payload == {
            "from": "Lunance <no-reply@lunance.app>",
            "to": ["ana@example.com"],
            "subject": "Asunto",
            "text": "Hola",
            "html": "<p>Hola</p>",
            "tags": [{"name": "category", "value": "verify-email"}],
        }

    async def test_error_status_raises_delivery_error(self):
        sender = ResendEmailSender(
            api_key="re_test",
            sender="x@lunance.app",
            transport=httpx.MockTransport(
                lambda request: httpx.Response(422, json={"message": "bad from"})
            ),
        )

        with pytest.raises(EmailDeliveryError, match="HTTP 422"):
            await sender.send(EMAIL)

    async def test_network_error_raises_delivery_error(self):
        def handler(request):
            raise httpx.ConnectError("down")

        sender = ResendEmailSender(
            api_key="re_test",
            sender="x@lunance.app",
            transport=httpx.MockTransport(handler),
        )

        with pytest.raises(EmailDeliveryError, match="sin respuesta"):
            await sender.send(EMAIL)

    async def test_requires_api_key(self):
        with pytest.raises(ValueError):
            ResendEmailSender(api_key="", sender="x@lunance.app")


@pytest.mark.unit
@pytest.mark.asyncio
class TestSmtpSender:
    async def test_sends_multipart_message(self, monkeypatch):
        sent: list[tuple] = []

        class FakeSMTP:
            def __init__(self, host, port, timeout):
                sent.append(("connect", host, port))

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def starttls(self):
                sent.append(("starttls",))

            def login(self, user, password):
                sent.append(("login", user))

            def send_message(self, message):
                sent.append(("send", message))

        monkeypatch.setattr(
            "infrastructure.external_services.email.smtp.smtplib.SMTP", FakeSMTP
        )
        sender = SmtpEmailSender(sender="Lunance <dev@lunance.local>", host="mailpit", port=1025)

        await sender.send(EMAIL)

        assert sent[0] == ("connect", "mailpit", 1025)
        message = sent[-1][1]
        assert message["To"] == "ana@example.com"
        assert message["Subject"] == "Asunto"
        assert message.is_multipart()
        assert {part.get_content_type() for part in message.iter_parts()} == {
            "text/plain",
            "text/html",
        }
        # Sin credenciales (Mailpit) no hay login ni STARTTLS.
        assert [step[0] for step in sent] == ["connect", "send"]

    async def test_connection_error_raises_delivery_error(self):
        sender = SmtpEmailSender(sender="x@lunance.local", host="127.0.0.1", port=1)

        with pytest.raises(EmailDeliveryError):
            await sender.send(EMAIL)


@pytest.mark.unit
@pytest.mark.asyncio
class TestDelivery:
    async def test_failure_is_logged_without_recipient(self, caplog):
        class Failing(InMemoryEmailSender):
            name = "failing"

            async def send(self, email):
                raise EmailDeliveryError(self.name, "HTTP 500")

        with caplog.at_level(logging.ERROR):
            await deliver(Failing(), EMAIL)

        assert "Email delivery failed" in caplog.text
        assert "ana@example.com" not in caplog.text

    async def test_success_goes_to_the_outbox(self):
        outbox = InMemoryEmailSender()

        await deliver(outbox, EMAIL)

        assert outbox.sent_to("ana@example.com") == [EMAIL]


@pytest.mark.unit
class TestEmailSettings:
    def test_defaults_per_environment(self):
        assert _settings(ENVIRONMENT="DEV").email_backend == "smtp"
        assert _settings(ENVIRONMENT="TEST").email_backend == "memory"

    def test_link_base_falls_back_to_frontend_url(self):
        settings = _settings(FRONTEND_URL="http://localhost:5173/")
        assert settings.email_link_base_url == "http://localhost:5173"
        settings = _settings(
            FRONTEND_URL="http://localhost:5173", EMAIL_LINK_BASE_URL="https://x.app"
        )
        assert settings.email_link_base_url == "https://x.app"

    def test_prod_requires_resend_with_api_key_and_https_links(self):
        with pytest.raises(ValidationError, match="RESEND_API_KEY"):
            _settings(ENVIRONMENT="PROD", EMAIL_LINK_BASE_URL="https://lunance.app")
        with pytest.raises(ValidationError, match="EMAIL_BACKEND=resend"):
            _settings(
                ENVIRONMENT="PROD",
                EMAIL_BACKEND="smtp",
                RESEND_API_KEY="re_x",
                EMAIL_LINK_BASE_URL="https://lunance.app",
            )
        with pytest.raises(ValidationError, match="https"):
            _settings(
                ENVIRONMENT="PROD",
                RESEND_API_KEY="re_x",
                EMAIL_LINK_BASE_URL="http://lunance.app",
            )

        prod = _settings(
            ENVIRONMENT="PROD",
            RESEND_API_KEY="re_x",
            EMAIL_LINK_BASE_URL="https://lunance.app",
        )
        assert isinstance(build_email_sender(prod), ResendEmailSender)

    def test_unknown_backend_is_rejected(self):
        with pytest.raises(ValidationError, match="EMAIL_BACKEND"):
            _settings(EMAIL_BACKEND="sendgrid")

    def test_factory_builds_each_backend(self):
        assert isinstance(build_email_sender(_settings()), SmtpEmailSender)
        assert isinstance(
            build_email_sender(_settings(ENVIRONMENT="TEST")), InMemoryEmailSender
        )


@pytest.mark.unit
@pytest.mark.asyncio
class TestRedisLoginThrottle:
    async def test_progressive_lock(self):
        redis = FakeAsyncRedis(decode_responses=True)
        throttle = RedisLoginThrottle(lambda: redis)

        for _ in range(RedisLoginThrottle.FREE_ATTEMPTS - 1):
            await throttle.record_failure("s")
        assert await throttle.retry_after("s") is None

        await throttle.record_failure("s")
        first = await throttle.retry_after("s")
        await throttle.record_failure("s")
        second = await throttle.retry_after("s")

        assert first and 0 < first <= 60
        assert second and 60 < second <= 120
        await throttle.reset("s")
        assert await throttle.retry_after("s") is None

    async def test_lock_never_exceeds_the_maximum(self):
        redis = FakeAsyncRedis(decode_responses=True)
        throttle = RedisLoginThrottle(lambda: redis)

        for _ in range(20):
            await throttle.record_failure("s")

        retry = await throttle.retry_after("s")
        assert retry and retry <= RedisLoginThrottle.MAX_LOCK_SECONDS

    async def test_subject_is_hashed_in_redis(self):
        redis = FakeAsyncRedis(decode_responses=True)
        throttle = RedisLoginThrottle(lambda: redis)

        await throttle.record_failure("email:ana@example.com")

        keys = await redis.keys("*")
        assert keys and all("ana" not in str(key) for key in keys)

    async def test_redis_down_raises_service_unavailable(self):
        throttle = RedisLoginThrottle(BrokenRedis)  # type: ignore[arg-type]

        with pytest.raises(ServiceTemporarilyUnavailableError):
            await throttle.retry_after("s")
        with pytest.raises(ServiceTemporarilyUnavailableError):
            await throttle.record_failure("s")
        with pytest.raises(ServiceTemporarilyUnavailableError):
            await throttle.reset("s")
