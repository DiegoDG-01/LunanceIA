"""Registro con correo, verificación, recuperación y cambio de contraseña, y throttle del
login por correo: handlers reales contra SQLite, Redis falso y reloj controlable."""

import re
from dataclasses import dataclass

import pytest
from sqlalchemy import func, select

from application.auth.commands.change_password import ChangePasswordCommand
from application.auth.commands.login import LoginCommand
from application.auth.commands.password_reset import (
    RequestPasswordResetCommand,
    ResetPasswordCommand,
)
from application.auth.commands.register import RegisterCommand
from application.auth.commands.verify_email import (
    ResendVerificationCommand,
    VerifyEmailCommand,
)
from application.auth.services.login_guard import LoginGuard
from domain.entities.auth.auth_event import AuthAction
from domain.entities.auth.session import RevocationReason
from infrastructure.cache.login_throttle import RedisLoginThrottle
from infrastructure.database.models.auth_event import AuthEventModel
from infrastructure.database.models.password_reset_token import (
    PasswordResetTokenModel,
)
from infrastructure.database.models.pending_signup import (
    EmailVerificationTokenModel,
    PendingSignupModel,
)
from infrastructure.database.models.user import UserModel
from shared.exceptions.application import (
    ServiceTemporarilyUnavailableError,
    TooManyAttemptsError,
)
from shared.exceptions.base import ValidationError
from shared.exceptions.domain import (
    EmailNotVerifiedError,
    InvalidCredentialsError,
    InvalidCurrentPasswordError,
    InvalidEmailTokenError,
    PasswordUnchangedError,
    UsernameAlreadyExistsError,
)

from .conftest import PASSWORD, AuthKit, BrokenRedis, context

pytestmark = pytest.mark.asyncio

NEW_PASSWORD = "Nueva!clave2026"
_TOKEN = re.compile(r"[?&]token=([A-Za-z0-9_\-]+)")


def _token(email) -> str:
    match = _TOKEN.search(email.text)
    assert match, email.text
    return match.group(1)


async def _count(kit: AuthKit, model, *where) -> int:
    stmt = select(func.count()).select_from(model)
    if where:
        stmt = stmt.where(*where)
    return (await kit.db.execute(stmt)).scalar_one()  # type: ignore[attr-defined]


async def _actions(kit: AuthKit) -> list[str]:
    rows = await kit.db.execute(  # type: ignore[attr-defined]
        select(AuthEventModel.action).order_by(AuthEventModel.id)
    )
    return list(rows.scalars().all())


async def _register(
    kit: AuthKit, email: str = "ana@example.com", username: str = "ana", **extra
) -> None:
    await kit.register_handler().handle(
        RegisterCommand(
            email=email,
            username=username,
            password=extra.pop("password", PASSWORD),
            context=context(),
        )
    )


@dataclass(frozen=True)
class Account:
    id: int
    email: str
    name: str


async def _signup(
    kit: AuthKit, email: str = "ana@example.com", username: str = "ana"
) -> Account:
    await _register(kit, email, username)
    user = await kit.verify_handler().handle(
        VerifyEmailCommand(token=_token(kit.queue.sent[-1]))
    )
    kit.queue.sent.clear()
    assert user.id is not None and user.email
    return Account(id=user.id, email=user.email, name=user.name)


class TestRegister:
    async def test_stores_pending_signup_and_sends_link_without_creating_user(
        self, kit: AuthKit
    ):
        await _register(kit, email="  Ana@Example.COM ")

        [email] = kit.queue.sent
        assert email.to == ["ana@example.com"]
        assert email.tag == "verify-email"
        assert "https://app.lunance.test/verify-email?token=" in email.text
        assert email.html and "Confirmar correo" in email.html
        assert await _count(kit, UserModel) == 0
        signup = (
            await kit.db.execute(select(PendingSignupModel))  # type: ignore[attr-defined]
        ).scalar_one()
        assert signup.email == "ana@example.com"
        # Solo hashes: ni la contraseña ni el token en claro.
        assert signup.password_hash.startswith("$argon2id$")
        stored = (
            await kit.db.execute(select(EmailVerificationTokenModel))  # type: ignore[attr-defined]
        ).scalar_one()
        assert stored.token_hash != _token(email) and len(stored.token_hash) == 64
        assert await _actions(kit) == ["signup.requested"]

    async def test_existing_account_gets_a_notice_and_nothing_is_stored(
        self, kit: AuthKit
    ):
        user = await kit.create_user(name="ana", email="ana@example.com")

        await _register(kit, email="ANA@example.com", username="otra")

        [email] = kit.queue.sent
        assert email.tag == "signup-existing-account"
        assert "token=" not in email.text
        assert await _count(kit, PendingSignupModel) == 0
        event = (
            await kit.db.execute(select(AuthEventModel))  # type: ignore[attr-defined]
        ).scalar_one()
        assert event.user_id == user.id
        assert event.details == {"email": "ana@example.com", "outcome": "existing_account"}

    async def test_username_taken_by_a_user_is_rejected(self, kit: AuthKit):
        await kit.create_user(name="ana")

        with pytest.raises(UsernameAlreadyExistsError):
            await _register(kit, email="otra@example.com", username="ana")
        assert kit.queue.sent == []

    async def test_username_reserved_by_another_open_signup(self, kit: AuthKit):
        await _register(kit, email="ana@example.com", username="ana")

        with pytest.raises(UsernameAlreadyExistsError):
            await _register(kit, email="otra@example.com", username="ana")

    async def test_expired_signup_releases_its_username(self, kit: AuthKit):
        await _register(kit, email="ana@example.com", username="ana")
        kit.clock.advance(days=8)

        await _register(kit, email="otra@example.com", username="ana")

        signup = (
            await kit.db.execute(select(PendingSignupModel))  # type: ignore[attr-defined]
        ).scalar_one()
        assert signup.email == "otra@example.com"

    async def test_registering_again_replaces_the_signup_and_old_links(
        self, kit: AuthKit
    ):
        await _register(kit, username="ana")
        first = _token(kit.queue.sent[-1])

        await _register(kit, username="ana2", password="Otra!clave99")
        second = _token(kit.queue.sent[-1])

        with pytest.raises(InvalidEmailTokenError):
            await kit.verify_handler().handle(VerifyEmailCommand(token=first))
        user = await kit.verify_handler().handle(VerifyEmailCommand(token=second))
        assert user.name == "ana2"
        assert await kit.hasher.verify("Otra!clave99", user.password or "")

    async def test_weak_password_is_rejected_before_storing(self, kit: AuthKit):
        with pytest.raises(ValidationError):
            await _register(kit, password="weakpassword")
        assert await _count(kit, PendingSignupModel) == 0


class TestVerifyEmail:
    async def test_creates_verified_user_and_consumes_the_signup(self, kit: AuthKit):
        await _register(kit, email="Ana@Example.com")
        token = _token(kit.queue.sent[-1])

        user = await kit.verify_handler().handle(VerifyEmailCommand(token=token))

        assert user.id and user.email == "ana@example.com" and user.email_verified
        assert user.name == "ana"
        assert await _count(kit, PendingSignupModel) == 0
        assert await _count(kit, EmailVerificationTokenModel) == 0
        assert (await _actions(kit))[-1] == "signup.verified"
        # La contraseña elegida al registrarse es la de la cuenta.
        issued = await kit.login_handler().handle(
            LoginCommand(email="ana@example.com", password=PASSWORD, context=context())
        )
        assert issued.access_token

    async def test_link_works_only_once(self, kit: AuthKit):
        await _register(kit)
        token = _token(kit.queue.sent[-1])
        await kit.verify_handler().handle(VerifyEmailCommand(token=token))

        with pytest.raises(InvalidEmailTokenError):
            await kit.verify_handler().handle(VerifyEmailCommand(token=token))
        assert await _count(kit, UserModel) == 1

    async def test_expired_link_is_rejected(self, kit: AuthKit):
        await _register(kit)
        token = _token(kit.queue.sent[-1])
        kit.clock.advance(hours=25)

        with pytest.raises(InvalidEmailTokenError):
            await kit.verify_handler().handle(VerifyEmailCommand(token=token))
        assert await _count(kit, UserModel) == 0

    async def test_unknown_token_is_rejected(self, kit: AuthKit):
        with pytest.raises(InvalidEmailTokenError):
            await kit.verify_handler().handle(VerifyEmailCommand(token="nope"))

    async def test_username_taken_meanwhile_releases_the_signup(self, kit: AuthKit):
        await _register(kit, username="ana")
        token = _token(kit.queue.sent[-1])
        # Otro camino (Google/Apple en la fase 3) creó una cuenta con ese username.
        await kit.create_user(name="ana", email="google@example.com")
        await kit.db.commit()  # type: ignore[attr-defined]

        with pytest.raises(UsernameAlreadyExistsError):
            await kit.verify_handler().handle(VerifyEmailCommand(token=token))
        assert await _count(kit, PendingSignupModel) == 0


class TestResendVerification:
    async def test_sends_another_link_and_keeps_the_previous_valid(self, kit: AuthKit):
        await _register(kit)
        first = _token(kit.queue.sent[-1])

        await kit.resend_handler().handle(
            ResendVerificationCommand(email="ANA@example.com")
        )

        assert len(kit.queue.sent) == 2
        second = _token(kit.queue.sent[-1])
        assert second != first
        user = await kit.verify_handler().handle(VerifyEmailCommand(token=first))
        assert user.email == "ana@example.com"
        assert "signup.verification_resent" in await _actions(kit)

    @pytest.mark.parametrize("case", ["unknown", "existing_account", "expired"])
    async def test_sends_nothing_without_an_open_signup(self, kit: AuthKit, case):
        if case == "existing_account":
            await kit.create_user(name="ana", email="ana@example.com")
        if case == "expired":
            await _register(kit)
            kit.queue.sent.clear()
            kit.clock.advance(days=8)

        await kit.resend_handler().handle(
            ResendVerificationCommand(email="ana@example.com")
        )

        assert kit.queue.sent == []


class TestForgotAndResetPassword:
    async def test_forgot_sends_single_use_link(self, kit: AuthKit):
        user = await _signup(kit)

        await kit.forgot_handler().handle(
            RequestPasswordResetCommand(email="Ana@Example.com", context=context())
        )

        [email] = kit.queue.sent
        assert email.tag == "reset-password"
        assert "https://app.lunance.test/reset-password?token=" in email.text
        stored = (
            await kit.db.execute(select(PasswordResetTokenModel))  # type: ignore[attr-defined]
        ).scalar_one()
        assert stored.user_id == user.id and stored.token_hash != _token(email)
        assert (await _actions(kit))[-1] == "password.reset_requested"

    async def test_forgot_for_unknown_email_sends_nothing(self, kit: AuthKit):
        await kit.forgot_handler().handle(
            RequestPasswordResetCommand(email="ghost@example.com")
        )

        assert kit.queue.sent == []
        assert await _count(kit, PasswordResetTokenModel) == 0

    async def test_forgot_for_pending_signup_explains_how_to_confirm(
        self, kit: AuthKit
    ):
        await _register(kit)
        kit.queue.sent.clear()

        await kit.forgot_handler().handle(
            RequestPasswordResetCommand(email="ana@example.com")
        )

        [email] = kit.queue.sent
        assert email.tag == "signup-pending"
        assert "token=" not in email.text
        assert "/verify-email/resend" in email.text

    async def test_reset_changes_password_and_revokes_every_session(
        self, kit: AuthKit
    ):
        user = await _signup(kit)
        model = await kit.db.get(UserModel, user.id)  # type: ignore[attr-defined]
        web = await kit.login(model, context())
        phone = await kit.login(model, context())
        await kit.forgot_handler().handle(RequestPasswordResetCommand(email=user.email))
        token = _token(kit.queue.sent[-1])

        await kit.reset_handler().handle(
            ResetPasswordCommand(token=token, password=NEW_PASSWORD, context=context())
        )

        assert await kit.sessions.list_active(user.id, kit.clock.now) == []
        for issued in (web, phone):
            assert await kit.redis.exists(f"revoked_sid:{issued.session.uuid}")  # type: ignore[attr-defined]
            stored = await kit.sessions.get(issued.session.id)  # type: ignore[arg-type]
            assert stored and stored.revoked_reason is RevocationReason.PASSWORD_RESET
        with pytest.raises(InvalidCredentialsError):
            await kit.login(model, context())
        issued = await kit.login_handler().handle(
            LoginCommand(email=user.email, password=NEW_PASSWORD, context=context())
        )
        assert issued.access_token
        assert kit.queue.sent[-1].tag == "password-changed"
        actions = await _actions(kit)
        assert "password.reset" in actions
        assert actions.count("session.revoked") >= 2

    async def test_reset_link_works_only_once(self, kit: AuthKit):
        user = await _signup(kit)
        await kit.forgot_handler().handle(RequestPasswordResetCommand(email=user.email))
        token = _token(kit.queue.sent[-1])
        await kit.reset_handler().handle(
            ResetPasswordCommand(token=token, password=NEW_PASSWORD)
        )

        with pytest.raises(InvalidEmailTokenError):
            await kit.reset_handler().handle(
                ResetPasswordCommand(token=token, password="Tercera!clave1")
            )

    async def test_using_one_link_invalidates_the_others(self, kit: AuthKit):
        user = await _signup(kit)
        for _ in range(2):
            await kit.forgot_handler().handle(
                RequestPasswordResetCommand(email=user.email)
            )
        first, second = (_token(email) for email in kit.queue.sent)

        await kit.reset_handler().handle(
            ResetPasswordCommand(token=second, password=NEW_PASSWORD)
        )

        with pytest.raises(InvalidEmailTokenError):
            await kit.reset_handler().handle(
                ResetPasswordCommand(token=first, password="Tercera!clave1")
            )

    async def test_expired_reset_link_is_rejected(self, kit: AuthKit):
        user = await _signup(kit)
        await kit.forgot_handler().handle(RequestPasswordResetCommand(email=user.email))
        token = _token(kit.queue.sent[-1])
        kit.clock.advance(hours=1, seconds=1)

        with pytest.raises(InvalidEmailTokenError):
            await kit.reset_handler().handle(
                ResetPasswordCommand(token=token, password=NEW_PASSWORD)
            )

    async def test_reset_requires_a_strong_password(self, kit: AuthKit):
        user = await _signup(kit)
        await kit.forgot_handler().handle(RequestPasswordResetCommand(email=user.email))

        with pytest.raises(ValidationError):
            await kit.reset_handler().handle(
                ResetPasswordCommand(
                    token=_token(kit.queue.sent[-1]), password="weakpassword"
                )
            )

    async def test_reset_clears_the_account_lock(self, kit: AuthKit):
        user = await _signup(kit)
        for _ in range(RedisLoginThrottle.ACCOUNT_FREE_ATTEMPTS):
            await kit.guard.record_failure(user.email, "198.51.100.9")
        assert (await kit.guard.locks(user.email, "203.0.113.5")).account
        await kit.forgot_handler().handle(RequestPasswordResetCommand(email=user.email))

        await kit.reset_handler().handle(
            ResetPasswordCommand(token=_token(kit.queue.sent[-1]), password=NEW_PASSWORD)
        )

        assert (await kit.guard.locks(user.email, "203.0.113.5")).account is None


class TestChangePassword:
    async def test_keeps_current_session_and_revokes_the_others(self, kit: AuthKit):
        user = await _signup(kit)
        model = await kit.db.get(UserModel, user.id)  # type: ignore[attr-defined]
        current = await kit.login(model, context())
        other = await kit.login(model, context())

        await kit.change_handler().handle(
            ChangePasswordCommand(
                user_id=user.id,
                session_uuid=current.session.uuid,
                current_password=PASSWORD,
                new_password=NEW_PASSWORD,
            )
        )

        active = await kit.sessions.list_active(user.id, kit.clock.now)
        assert [s.uuid for s in active] == [current.session.uuid]
        assert await kit.revocations.is_revoked(other.session.uuid)
        assert not await kit.revocations.is_revoked(current.session.uuid)
        revoked = await kit.sessions.get(other.session.id)  # type: ignore[arg-type]
        assert revoked and revoked.revoked_reason is RevocationReason.PASSWORD_CHANGE
        reloaded = await kit.users.get_by_id(user.id)
        assert reloaded and await kit.hasher.verify(NEW_PASSWORD, reloaded.password or "")
        assert kit.queue.sent[-1].tag == "password-changed"
        assert (await _actions(kit))[-1] == "password.changed"

    async def test_wrong_current_password(self, kit: AuthKit):
        user = await _signup(kit)

        with pytest.raises(InvalidCurrentPasswordError):
            await kit.change_handler().handle(
                ChangePasswordCommand(
                    user_id=user.id,
                    session_uuid="s",
                    current_password="Wrong-pass1",
                    new_password=NEW_PASSWORD,
                )
            )

    async def test_new_password_must_differ(self, kit: AuthKit):
        user = await _signup(kit)

        with pytest.raises(PasswordUnchangedError):
            await kit.change_handler().handle(
                ChangePasswordCommand(
                    user_id=user.id,
                    session_uuid="s",
                    current_password=PASSWORD,
                    new_password=PASSWORD,
                )
            )

    async def test_invalidates_pending_reset_links(self, kit: AuthKit):
        user = await _signup(kit)
        model = await kit.db.get(UserModel, user.id)  # type: ignore[attr-defined]
        current = await kit.login(model, context())
        await kit.forgot_handler().handle(RequestPasswordResetCommand(email=user.email))
        token = _token(kit.queue.sent[-1])

        await kit.change_handler().handle(
            ChangePasswordCommand(
                user_id=user.id,
                session_uuid=current.session.uuid,
                current_password=PASSWORD,
                new_password=NEW_PASSWORD,
            )
        )

        with pytest.raises(InvalidEmailTokenError):
            await kit.reset_handler().handle(
                ResetPasswordCommand(token=token, password="Tercera!clave1")
            )


class TestLoginByEmail:
    async def test_email_is_case_and_space_insensitive(self, kit: AuthKit):
        await _signup(kit, email="ana@example.com")

        issued = await kit.login_handler().handle(
            LoginCommand(email="  ANA@Example.com ", password=PASSWORD, context=context())
        )

        assert issued.access_token

    async def test_pending_signup_password_says_email_not_verified(self, kit: AuthKit):
        await _register(kit)

        with pytest.raises(EmailNotVerifiedError):
            await kit.login_handler().handle(
                LoginCommand(email="ana@example.com", password=PASSWORD, context=context())
            )

    async def test_pending_signup_with_wrong_password_is_invalid_credentials(
        self, kit: AuthKit
    ):
        await _register(kit)

        with pytest.raises(InvalidCredentialsError):
            await kit.login_handler().handle(
                LoginCommand(
                    email="ana@example.com", password="Wrong-pass1", context=context()
                )
            )

    async def test_ip_lock_after_repeated_failures(self, kit: AuthKit):
        user = await _signup(kit)
        ctx = context(ip="198.51.100.7")
        for _ in range(RedisLoginThrottle.FREE_ATTEMPTS):
            with pytest.raises(InvalidCredentialsError):
                await kit.login_handler().handle(
                    LoginCommand(email=user.email, password="Wrong-pass1", context=ctx)
                )

        # Ni la contraseña correcta entra desde esa IP mientras dure el bloqueo.
        with pytest.raises(TooManyAttemptsError) as raised:
            await kit.login_handler().handle(
                LoginCommand(email=user.email, password=PASSWORD, context=ctx)
            )
        assert 0 < raised.value.retry_after <= RedisLoginThrottle.BASE_LOCK_SECONDS
        # Desde otra IP, el dueño sigue entrando.
        issued = await kit.login_handler().handle(
            LoginCommand(email=user.email, password=PASSWORD, context=context())
        )
        assert issued.access_token
        throttled = (
            await kit.db.execute(  # type: ignore[attr-defined]
                select(AuthEventModel).where(
                    AuthEventModel.action == AuthAction.LOGIN_THROTTLED.value
                )
            )
        ).scalar_one()
        assert throttled.details == {"email": user.email, "scope": "ip"}

    async def test_account_lock_spares_known_devices(self, kit: AuthKit):
        user = await _signup(kit)
        model = await kit.db.get(UserModel, user.id)  # type: ignore[attr-defined]
        known = context()
        await kit.login(model, known)
        # Ataque repartido entre muchas IPs.
        for attempt in range(RedisLoginThrottle.ACCOUNT_FREE_ATTEMPTS):
            await kit.guard.record_failure(user.email, f"198.51.100.{attempt}")

        with pytest.raises(TooManyAttemptsError):
            await kit.login_handler().handle(
                LoginCommand(email=user.email, password=PASSWORD, context=context())
            )
        issued = await kit.login_handler().handle(
            LoginCommand(email=user.email, password=PASSWORD, context=known)
        )
        assert issued.access_token

    async def test_success_resets_the_failure_counter(self, kit: AuthKit):
        user = await _signup(kit)
        ctx = context(ip="198.51.100.8")
        for _ in range(RedisLoginThrottle.FREE_ATTEMPTS - 1):
            with pytest.raises(InvalidCredentialsError):
                await kit.login_handler().handle(
                    LoginCommand(email=user.email, password="Wrong-pass1", context=ctx)
                )
        await kit.login_handler().handle(
            LoginCommand(email=user.email, password=PASSWORD, context=ctx)
        )

        with pytest.raises(InvalidCredentialsError):
            await kit.login_handler().handle(
                LoginCommand(email=user.email, password="Wrong-pass1", context=ctx)
            )
        # Un fallo tras el reinicio no bloquea.
        assert (await kit.guard.locks(user.email, ctx.ip)).ip is None

    async def test_redis_down_rejects_login_with_503(self, kit: AuthKit):
        user = await _signup(kit)
        kit.guard = LoginGuard(
            per_ip=RedisLoginThrottle(BrokenRedis),  # type: ignore[arg-type]
            per_account=RedisLoginThrottle.per_account(BrokenRedis),  # type: ignore[arg-type]
        )

        with pytest.raises(ServiceTemporarilyUnavailableError):
            await kit.login_handler().handle(
                LoginCommand(email=user.email, password=PASSWORD, context=context())
            )


class TestPurge:
    async def test_purges_expired_signups_and_used_or_expired_reset_tokens(
        self, kit: AuthKit
    ):
        user = await _signup(kit, email="ana@example.com", username="ana")
        await kit.forgot_handler().handle(RequestPasswordResetCommand(email=user.email))
        used = _token(kit.queue.sent[-1])
        await kit.reset_handler().handle(
            ResetPasswordCommand(token=used, password=NEW_PASSWORD)
        )
        await kit.forgot_handler().handle(RequestPasswordResetCommand(email=user.email))
        await _register(kit, email="pendiente@example.com", username="pendiente")
        kit.clock.advance(hours=2)
        await _register(kit, email="nuevo@example.com", username="nuevo")

        first = await kit.purge_handler().handle()

        # El enlace usado y el que caducó (1 h) se van; el registro de hace 2 h sigue.
        assert first.password_reset_tokens == 2
        assert first.pending_signups == 0
        kit.clock.advance(days=7, seconds=1)
        second = await kit.purge_handler().handle()
        assert second.pending_signups == 2
        assert await _count(kit, PendingSignupModel) == 0
        assert await _count(kit, EmailVerificationTokenModel) == 0
