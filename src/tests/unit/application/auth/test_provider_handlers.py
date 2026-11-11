"""Entrar con Google y Apple, vincular y desvincular, avisos de Apple y cuentas sin
contraseña: handlers reales contra SQLite, Redis falso y proveedores falsos (sin red)."""

import json
from dataclasses import dataclass

import pytest
from sqlalchemy import func, select

from application.auth.commands.apple_notifications import (
    AppleNotificationCommand,
    AppleNotificationHandler,
)
from application.auth.commands.change_password import ChangePasswordCommand
from application.auth.commands.change_username import (
    ChangeUsernameCommand,
    ChangeUsernameHandler,
)
from application.auth.commands.link_provider import (
    LinkProviderCommand,
    LinkProviderHandler,
    UnlinkProviderCommand,
    UnlinkProviderHandler,
)
from application.auth.commands.login import LoginCommand
from application.auth.commands.password_reset import (
    RequestPasswordResetCommand,
    ResetPasswordCommand,
)
from application.auth.commands.provider_sign_in import (
    ProviderSignInCommand,
    ProviderSignInHandler,
    ProviderTokenGate,
)
from application.auth.commands.register import RegisterCommand
from application.auth.services.apple_tokens import (
    AppleAuthorizationRevoker,
    AppleTokenVault,
)
from application.auth.services.external_accounts import ExternalAccounts
from application.interfaces.identity_providers import IdentityProvider
from domain.entities.auth.auth_event import AuthAction
from domain.entities.auth.session import Platform, RevocationReason
from infrastructure.cache.provider_tokens import RedisUsedProviderTokens
from infrastructure.database.models.auth_event import AuthEventModel
from infrastructure.database.models.pending_signup import PendingSignupModel
from infrastructure.database.models.user import UserModel
from infrastructure.database.models.user_session import UserSessionModel
from infrastructure.security.secret_cipher import AesGcmSecretCipher
from shared.exceptions.application import (
    InvalidProviderTokenError,
    ProviderNotConfiguredError,
    ServiceTemporarilyUnavailableError,
)
from shared.exceptions.domain import (
    InvalidCredentialsError,
    InvalidCurrentPasswordError,
    LastLoginMethodError,
    PasswordNotSetError,
    ProviderAccountConflictError,
    ProviderAlreadyLinkedError,
    ProviderLinkRequiredError,
    RecentLoginRequiredError,
    UserInactiveError,
    UsernameAlreadyExistsError,
)
from tests.identity_providers import (
    APPLE_SERVICES_ID,
    ENCRYPTION_SECRET,
    NONCE,
    FakeApple,
    FakeGoogle,
    apple_client,
    google_verifier,
)

from .conftest import PASSWORD, AuthKit, BrokenRedis, context

NEW_PASSWORD = "Nueva!clave2026"


@dataclass
class Providers:
    kit: AuthKit
    google: FakeGoogle
    apple: FakeApple
    gate: ProviderTokenGate
    vault: AppleTokenVault
    revoker: AppleAuthorizationRevoker
    suffixes: list[str]

    def accounts(self) -> ExternalAccounts:
        suffixes = iter(self.suffixes)
        return ExternalAccounts(
            user_repository=self.kit.users,
            pending_signup_repository=self.kit.pending,
            username_suffix=lambda: next(suffixes),
        )

    def sign_in_handler(
        self, gate: ProviderTokenGate | None = None
    ) -> ProviderSignInHandler:
        kit = self.kit
        return ProviderSignInHandler(
            gate=gate or self.gate,
            accounts=self.accounts(),
            user_repository=kit.users,
            auth_event_repository=kit.events,
            session_manager=kit.manager(),
            revocations=kit.revocations,
            email_queue=kit.queue,
            email_config=kit.email_config,
            uow=kit.uow,
            apple_tokens=self.vault,
            now=kit.clock,
        )

    def link_handler(self) -> LinkProviderHandler:
        kit = self.kit
        return LinkProviderHandler(
            gate=self.gate,
            session_repository=kit.sessions,
            password_hasher=kit.hasher,
            apple_tokens=self.vault,
            user_repository=kit.users,
            auth_event_repository=kit.events,
            email_queue=kit.queue,
            email_config=kit.email_config,
            uow=kit.uow,
            now=kit.clock,
        )

    def unlink_handler(self) -> UnlinkProviderHandler:
        kit = self.kit
        return UnlinkProviderHandler(
            apple_tokens=self.vault,
            apple_revoker=self.revoker,
            user_repository=kit.users,
            auth_event_repository=kit.events,
            email_queue=kit.queue,
            email_config=kit.email_config,
            uow=kit.uow,
            now=kit.clock,
        )

    def notification_handler(self) -> AppleNotificationHandler:
        kit = self.kit
        return AppleNotificationHandler(
            apple=self.gate.apple,
            user_repository=kit.users,
            session_repository=kit.sessions,
            auth_event_repository=kit.events,
            revocations=kit.revocations,
            uow=kit.uow,
            now=kit.clock,
        )

    async def google_sign_in(self, token: str, ctx=None, **extra):
        return await self.sign_in_handler().handle(
            ProviderSignInCommand(
                provider=IdentityProvider.GOOGLE,
                id_token=token,
                context=ctx or context(),
                **extra,
            )
        )

    async def apple_sign_in(self, token: str, ctx=None, nonce: str = NONCE, **extra):
        return await self.sign_in_handler().handle(
            ProviderSignInCommand(
                provider=IdentityProvider.APPLE,
                id_token=token,
                nonce=nonce,
                context=ctx or context(platform=Platform.IOS),
                **extra,
            )
        )


@pytest.fixture
def providers(kit: AuthKit) -> Providers:
    google, apple = FakeGoogle(), FakeApple()
    apple_gateway, _ = apple_client(apple)
    gate = ProviderTokenGate(
        google=google_verifier(google),
        apple=apple_gateway,
        used_tokens=RedisUsedProviderTokens(lambda: kit.redis),  # type: ignore[arg-type]
    )
    vault = AppleTokenVault(
        cipher=AesGcmSecretCipher(ENCRYPTION_SECRET, purpose="apple-refresh-token"),
        user_repository=kit.users,
    )
    return Providers(
        kit=kit,
        google=google,
        apple=apple,
        gate=gate,
        vault=vault,
        revoker=AppleAuthorizationRevoker(vault=vault, apple=apple_gateway),
        suffixes=["1111", "2222", "3333"],
    )


async def _events(kit: AuthKit, action: AuthAction) -> list[AuthEventModel]:
    rows = await kit.db.execute(  # type: ignore[attr-defined]
        select(AuthEventModel)
        .where(AuthEventModel.action == action.value)
        .order_by(AuthEventModel.id)
    )
    return list(rows.scalars().all())


def _details(event: AuthEventModel) -> dict:
    assert event.details is not None
    return event.details


async def _committed_user(kit: AuthKit, **fields) -> int:
    """`create_user` solo hace flush: un handler que falla y hace rollback lo borraría.
    Devuelve el id (tras un rollback, los atributos del modelo caducan)."""
    user = await kit.create_user(**fields)
    await kit.uow.commit()
    return user.id


async def _user(kit: AuthKit, user_id: int) -> UserModel:
    kit.db.expire_all()  # type: ignore[attr-defined]
    return await kit.db.get(UserModel, user_id)  # type: ignore[attr-defined]


class TestNewAccounts:
    async def test_google_creates_a_verified_account_without_password(self, providers):
        kit = providers.kit
        token = providers.google.id_token(sub="g-1", email="Ana.Lopez@Gmail.com")

        result = await providers.google_sign_in(token)

        assert result.account_created and not result.provider_linked
        user = await _user(kit, result.user.id)
        assert user.email == "ana.lopez@gmail.com"
        assert user.email_verified is True
        assert user.password is None
        assert user.google_sub == "g-1" and user.apple_sub is None
        assert user.name == "analopez"
        assert result.issued.session.user_id == user.id
        [signup] = await _events(kit, AuthAction.SIGNUP_VERIFIED)
        assert signup.details == {"email": "ana.lopez@gmail.com", "method": "google"}
        [login] = await _events(kit, AuthAction.LOGIN_SUCCEEDED)
        assert _details(login)["method"] == "google"
        assert _details(login)["account_created"] is True
        assert token not in json.dumps(login.details)
        assert kit.queue.sent == []

    async def test_username_collision_gets_a_suffix(self, providers):
        kit = providers.kit
        await kit.create_user(name="analopez", email="otra@example.com")
        await kit.register_handler().handle(
            RegisterCommand(
                email="pendiente@example.com",
                username="analopez_1111",
                password=PASSWORD,
                context=context(),
            )
        )

        result = await providers.google_sign_in(providers.google.id_token())

        # "analopez" es de una cuenta y "analopez_1111" lo aparta un registro pendiente.
        assert result.user.name == "analopez_2222"

    async def test_falls_back_to_the_email_and_then_to_usuario(self, providers):
        first = await providers.google_sign_in(
            providers.google.id_token(name=None, email="diego.dg@gmail.com")
        )
        second = await providers.google_sign_in(
            providers.google.id_token(name="李", email="42@gmail.com")
        )

        assert first.user.name == "diego.dg"
        assert second.user.name == "usuario"

    async def test_pending_signup_with_the_same_email_is_discarded(self, providers):
        kit = providers.kit
        await kit.register_handler().handle(
            RegisterCommand(
                email="ana@gmail.com",
                username="ana_pendiente",
                password=PASSWORD,
                context=context(),
            )
        )

        await providers.google_sign_in(providers.google.id_token(email="ana@gmail.com"))

        count = await kit.db.execute(  # type: ignore[attr-defined]
            select(func.count()).select_from(PendingSignupModel)
        )
        assert count.scalar_one() == 0

    async def test_apple_uses_the_name_sent_by_the_app(self, providers):
        result = await providers.apple_sign_in(
            providers.apple.identity_token(), name="Diego Domínguez"
        )

        assert result.account_created
        assert result.user.name == "diegodominguez"
        assert result.user.email.endswith("@privaterelay.appleid.com")

    async def test_apple_without_email_cannot_create_an_account(self, providers):
        with pytest.raises(InvalidProviderTokenError) as caught:
            await providers.apple_sign_in(providers.apple.identity_token(email=None))

        assert caught.value.reason == "email_missing"
        [failed] = await _events(providers.kit, AuthAction.LOGIN_FAILED)
        assert failed.details == {"method": "apple", "reason": "email_missing"}


class TestExistingAccounts:
    async def test_linked_subject_signs_in_even_if_the_email_changed(self, providers):
        kit = providers.kit
        user = await kit.create_user(email="viejo@empresa.com", google_sub="g-7")

        result = await providers.google_sign_in(
            providers.google.id_token(sub="g-7", email="nuevo@gmail.com")
        )

        assert result.user.id == user.id
        assert not result.account_created and not result.provider_linked
        assert (await _user(kit, user.id)).email == "viejo@empresa.com"

    async def test_gmail_account_is_linked_and_notified(self, providers):
        kit = providers.kit
        user = await kit.create_user(email="ana@gmail.com")

        result = await providers.google_sign_in(
            providers.google.id_token(sub="g-2", email="ANA@gmail.com")
        )

        assert result.provider_linked and result.user.id == user.id
        assert (await _user(kit, user.id)).google_sub == "g-2"
        [linked] = await _events(kit, AuthAction.PROVIDER_LINKED)
        assert linked.details == {"provider": "google", "mode": "email"}
        [mail] = kit.queue.to("ana@gmail.com")
        assert "Google" in mail.subject and mail.tag == "provider-linked"

    async def test_workspace_domain_is_linked(self, providers):
        kit = providers.kit
        await kit.create_user(email="ana@empresa.com")

        result = await providers.google_sign_in(
            providers.google.id_token(email="ana@empresa.com", hd="empresa.com")
        )

        assert result.provider_linked

    @pytest.mark.parametrize(
        ("email", "hd"),
        [
            ("ana@empresa.com", None),
            ("ana@icloud.com", None),
            ("ana@empresa.com", "otra.com"),
        ],
    )
    async def test_other_mailboxes_require_linking_from_settings(
        self, providers, email, hd
    ):
        kit = providers.kit
        user_id = await _committed_user(kit, email=email)

        with pytest.raises(ProviderLinkRequiredError) as caught:
            await providers.google_sign_in(
                providers.google.id_token(email=email, hd=hd)
            )

        assert caught.value.login_methods == ["password"]
        assert (await _user(kit, user_id)).google_sub is None
        [failed] = await _events(kit, AuthAction.LOGIN_FAILED)
        assert _details(failed)["reason"] == "link_required"
        assert await _events(kit, AuthAction.LOGIN_SUCCEEDED) == []
        assert kit.queue.sent == []

    async def test_apple_links_icloud_and_private_relay(self, providers):
        kit = providers.kit
        icloud = await kit.create_user(email="ana@icloud.com")
        relay = await kit.create_user(email="x1y2@privaterelay.appleid.com")

        first = await providers.apple_sign_in(
            providers.apple.identity_token(
                email="ana@icloud.com", is_private_email=None
            )
        )
        second = await providers.apple_sign_in(
            providers.apple.identity_token(email="x1y2@privaterelay.appleid.com")
        )

        assert first.user.id == icloud.id and first.provider_linked
        assert second.user.id == relay.id and second.provider_linked

    async def test_apple_does_not_link_gmail(self, providers):
        await providers.kit.create_user(email="ana@gmail.com")

        with pytest.raises(ProviderLinkRequiredError):
            await providers.apple_sign_in(
                providers.apple.identity_token(email="ana@gmail.com")
            )

    async def test_account_linked_to_another_google_account_is_not_replaced(
        self, providers
    ):
        kit = providers.kit
        await kit.create_user(email="ana@gmail.com", google_sub="g-old")

        with pytest.raises(ProviderAccountConflictError):
            await providers.google_sign_in(
                providers.google.id_token(sub="g-new", email="ana@gmail.com")
            )

    async def test_inactive_account_is_rejected(self, providers):
        kit = providers.kit
        await kit.create_user(email="ana@gmail.com", google_sub="g-9", is_active=False)

        with pytest.raises(UserInactiveError):
            await providers.google_sign_in(providers.google.id_token(sub="g-9"))

        [failed] = await _events(kit, AuthAction.LOGIN_FAILED)
        assert _details(failed)["reason"] == "inactive"

    async def test_same_device_replaces_its_session(self, providers):
        kit = providers.kit
        ctx = context()
        first = await providers.google_sign_in(
            providers.google.id_token(sub="g-3"), ctx
        )
        second = await providers.google_sign_in(
            providers.google.id_token(sub="g-3"), ctx
        )

        active = await kit.sessions.list_active(first.user.id, kit.clock.now)
        assert [s.uuid for s in active] == [second.issued.session.uuid]
        assert await kit.revocations.is_revoked(first.issued.session.uuid)


class TestTokenChecks:
    async def test_each_token_signs_in_once(self, providers):
        kit = providers.kit
        token = providers.google.id_token()
        await providers.google_sign_in(token)

        with pytest.raises(InvalidProviderTokenError) as caught:
            await providers.google_sign_in(token)

        assert caught.value.reason == "replay"
        [replay] = await _events(kit, AuthAction.PROVIDER_TOKEN_REPLAY)
        assert replay.details == {"method": "google"}

    async def test_invalid_token_is_audited_without_the_token(self, providers):
        kit = providers.kit
        token = providers.google.id_token(aud="otro")

        with pytest.raises(InvalidProviderTokenError):
            await providers.google_sign_in(token)

        [failed] = await _events(kit, AuthAction.LOGIN_FAILED)
        assert failed.details == {"method": "google", "reason": "audience"}

    async def test_redis_down_rejects_with_503(self, providers):
        gate = ProviderTokenGate(
            google=providers.gate.google,
            apple=None,
            used_tokens=RedisUsedProviderTokens(lambda: BrokenRedis()),  # type: ignore[arg-type]
        )

        with pytest.raises(ServiceTemporarilyUnavailableError):
            await providers.sign_in_handler(gate).handle(
                ProviderSignInCommand(
                    provider=IdentityProvider.GOOGLE,
                    id_token=providers.google.id_token(),
                    context=context(),
                )
            )
        assert await _events(providers.kit, AuthAction.LOGIN_SUCCEEDED) == []

    async def test_provider_not_configured(self, providers):
        gate = ProviderTokenGate(
            google=None, apple=None, used_tokens=providers.gate.used_tokens
        )

        with pytest.raises(ProviderNotConfiguredError):
            await providers.sign_in_handler(gate).handle(
                ProviderSignInCommand(
                    provider=IdentityProvider.APPLE, id_token="x", context=context()
                )
            )


class TestAppleRefreshToken:
    async def test_code_is_exchanged_with_the_token_audience_and_stored_encrypted(
        self, providers
    ):
        kit = providers.kit
        token = providers.apple.identity_token(aud=APPLE_SERVICES_ID)

        result = await providers.apple_sign_in(
            token, ctx=context(), authorization_code="code-1"
        )

        stored = (await _user(kit, result.user.id)).apple_refresh_token
        assert stored and stored.startswith("v1.") and "code-1" not in stored
        tokens = await providers.vault.load(result.user.id)
        assert tokens is not None
        assert tokens.client_id == APPLE_SERVICES_ID
        assert tokens.refresh_token.endswith(".code-1")

    async def test_rejected_code_rejects_the_sign_in(self, providers):
        providers.apple.token_status = 400

        with pytest.raises(InvalidProviderTokenError) as caught:
            await providers.apple_sign_in(
                providers.apple.identity_token(), authorization_code="used"
            )

        assert caught.value.reason == "authorization_code"

    async def test_code_of_another_apple_user_is_rejected(self, providers):
        providers.apple.token_subject = "000999.otro.0001"

        with pytest.raises(InvalidProviderTokenError) as caught:
            await providers.apple_sign_in(
                providers.apple.identity_token(sub="000123.yo.0042"),
                authorization_code="code",
            )

        assert caught.value.reason == "authorization_code_subject"

    async def test_apple_down_still_signs_in_without_the_token(self, providers):
        providers.apple.token_status = 503

        result = await providers.apple_sign_in(
            providers.apple.identity_token(), authorization_code="code"
        )

        assert result.account_created
        assert await providers.vault.load(result.user.id) is None

    async def test_revoker_revokes_and_clears_the_stored_token(self, providers):
        kit = providers.kit
        result = await providers.apple_sign_in(
            providers.apple.identity_token(), authorization_code="code-9"
        )

        assert await providers.revoker.revoke_for_user(result.user.id) is True
        await kit.uow.commit()

        assert providers.apple.revoked[0].endswith(".code-9")
        assert (await _user(kit, result.user.id)).apple_refresh_token is None
        assert await providers.revoker.revoke_for_user(result.user.id) is False

    async def test_token_copied_to_another_row_does_not_decrypt(self, providers):
        kit = providers.kit
        result = await providers.apple_sign_in(
            providers.apple.identity_token(), authorization_code="code"
        )
        other_id = (await kit.create_user()).id
        stored = (await _user(kit, result.user.id)).apple_refresh_token
        await kit.users.set_apple_refresh_token(other_id, stored)

        assert await providers.vault.load(other_id) is None


class TestLinkFromSettings:
    async def _link(self, providers, user, provider, token, **extra):
        extra.setdefault("current_password", PASSWORD)
        return await providers.link_handler().handle(
            LinkProviderCommand(
                user_id=user.id,
                session_uuid="s-1",
                provider=provider,
                id_token=token,
                context=context(),
                **extra,
            )
        )

    async def test_password_account_must_confirm_with_its_password(self, providers):
        kit = providers.kit
        user = await kit.create_user()
        token = providers.google.id_token(sub="g-9")

        with pytest.raises(RecentLoginRequiredError):
            await self._link(
                providers, user, IdentityProvider.GOOGLE, token, current_password=None
            )
        # El ID token no se gastó: con la contraseña, el mismo token vincula.
        linked = await self._link(providers, user, IdentityProvider.GOOGLE, token)

        assert linked.login_methods == ["password", "google"]

    async def test_wrong_password_is_rejected_and_audited(self, providers):
        kit = providers.kit
        user = await kit.create_user()

        with pytest.raises(InvalidCurrentPasswordError):
            await self._link(
                providers,
                user,
                IdentityProvider.GOOGLE,
                providers.google.id_token(),
                current_password="Otra!clave2026",
            )

        assert (await _user(kit, user.id)).google_sub is None
        [event] = await _events(kit, AuthAction.LOGIN_FAILED)
        assert event.details == {
            "method": "password",
            "reason": "invalid_password",
            "mode": "link",
            "provider": "google",
        }

    async def test_account_without_password_needs_a_recent_login(self, providers):
        kit = providers.kit
        result = await providers.apple_sign_in(providers.apple.identity_token())
        session_uuid = result.issued.session.uuid

        async def link():
            return await providers.link_handler().handle(
                LinkProviderCommand(
                    user_id=result.user.id,
                    session_uuid=session_uuid,
                    provider=IdentityProvider.GOOGLE,
                    id_token=providers.google.id_token(),
                    context=context(),
                )
            )

        kit.clock.advance(minutes=11)
        with pytest.raises(RecentLoginRequiredError):
            await link()
        kit.clock.advance(minutes=-2)  # 9 minutos después del login
        linked = await link()

        assert linked.login_methods == ["google", "apple"]

    async def test_links_google_with_any_email_and_notifies(self, providers):
        kit = providers.kit
        user = await kit.create_user(email="ana@empresa.com")

        linked = await self._link(
            providers,
            user,
            IdentityProvider.GOOGLE,
            providers.google.id_token(sub="g-5", email="otra@gmail.com"),
        )

        assert linked.login_methods == ["password", "google"]
        [event] = await _events(kit, AuthAction.PROVIDER_LINKED)
        assert event.details == {
            "provider": "google",
            "mode": "manual",
            "session_uuid": "s-1",
        }
        assert kit.queue.to("ana@empresa.com")[0].tag == "provider-linked"

    async def test_links_apple_and_stores_its_token(self, providers):
        user = await providers.kit.create_user()

        linked = await self._link(
            providers,
            user,
            IdentityProvider.APPLE,
            providers.apple.identity_token(),
            nonce=NONCE,
            authorization_code="code-2",
        )

        assert "apple" in linked.login_methods
        assert (await providers.vault.load(user.id)) is not None

    async def test_provider_account_of_another_user_is_rejected(self, providers):
        kit = providers.kit
        await kit.create_user(google_sub="g-taken")
        user = await kit.create_user()

        with pytest.raises(ProviderAlreadyLinkedError):
            await self._link(
                providers,
                user,
                IdentityProvider.GOOGLE,
                providers.google.id_token(sub="g-taken"),
            )

    async def test_second_google_account_is_rejected(self, providers):
        user = await providers.kit.create_user(google_sub="g-mine")

        with pytest.raises(ProviderAccountConflictError):
            await self._link(
                providers,
                user,
                IdentityProvider.GOOGLE,
                providers.google.id_token(sub="g-other"),
            )

    async def test_linking_the_same_account_again_is_a_no_op(self, providers):
        kit = providers.kit
        user = await kit.create_user(google_sub="g-mine")

        await self._link(
            providers,
            user,
            IdentityProvider.GOOGLE,
            providers.google.id_token(sub="g-mine"),
        )

        assert await _events(kit, AuthAction.PROVIDER_LINKED) == []

    async def test_replayed_token_cannot_link(self, providers):
        user = await providers.kit.create_user()
        token = providers.google.id_token()
        await providers.google_sign_in(token)

        with pytest.raises(InvalidProviderTokenError):
            await self._link(providers, user, IdentityProvider.GOOGLE, token)


class TestUnlink:
    async def _unlink(self, providers, user, provider):
        return await providers.unlink_handler().handle(
            UnlinkProviderCommand(
                user_id=user.id,
                session_uuid="s-1",
                provider=provider,
                context=context(),
            )
        )

    async def test_unlinks_google_when_a_password_remains(self, providers):
        kit = providers.kit
        user = await kit.create_user(google_sub="g-1")

        result = await self._unlink(providers, user, IdentityProvider.GOOGLE)

        assert result.login_methods == ["password"]
        [event] = await _events(kit, AuthAction.PROVIDER_UNLINKED)
        assert event.details == {"provider": "google", "session_uuid": "s-1"}
        assert kit.queue.to(user.email)[0].tag == "provider-unlinked"

    async def test_never_removes_the_last_login_method(self, providers):
        result = await providers.google_sign_in(providers.google.id_token())

        with pytest.raises(LastLoginMethodError):
            await self._unlink(providers, result.user, IdentityProvider.GOOGLE)

        assert (await _user(providers.kit, result.user.id)).google_sub is not None

    async def test_unlinking_apple_revokes_and_drops_its_token(self, providers):
        kit = providers.kit
        result = await providers.apple_sign_in(
            providers.apple.identity_token(), authorization_code="code-3"
        )
        await self._link_google(providers, result)

        methods = await self._unlink(providers, result.user, IdentityProvider.APPLE)

        assert methods.login_methods == ["google"]
        assert (await _user(kit, result.user.id)).apple_refresh_token is None
        assert providers.apple.revoked[0].endswith(".code-3")

    async def test_unlinking_what_is_not_linked_does_nothing(self, providers):
        kit = providers.kit
        user = await kit.create_user()

        await self._unlink(providers, user, IdentityProvider.APPLE)

        assert await _events(kit, AuthAction.PROVIDER_UNLINKED) == []

    async def _link_google(self, providers, result):
        # Cuenta sin contraseña: vale porque la sesión del login es reciente.
        await providers.link_handler().handle(
            LinkProviderCommand(
                user_id=result.user.id,
                session_uuid=result.issued.session.uuid,
                provider=IdentityProvider.GOOGLE,
                id_token=providers.google.id_token(),
                context=context(),
            )
        )


class TestAppleNotifications:
    async def _notify(self, providers, event, sub):
        return await providers.notification_handler().handle(
            AppleNotificationCommand(payload=providers.apple.notification(event, sub))
        )

    async def _apple_user(self, providers, sub="000123.ana.0042"):
        result = await providers.apple_sign_in(
            providers.apple.identity_token(sub=sub), authorization_code="code"
        )
        await providers.apple_sign_in(providers.apple.identity_token(sub=sub))
        return result.user

    async def test_consent_revoked_closes_sessions_and_keeps_the_link(self, providers):
        kit = providers.kit
        user = await self._apple_user(providers)

        result = await self._notify(providers, "consent-revoked", user.apple_sub)

        assert result.matched and result.sessions_revoked == 2 and not result.unlinked
        assert await kit.sessions.list_active(user.id, kit.clock.now) == []
        stored = await _user(kit, user.id)
        assert stored.apple_sub == user.apple_sub
        assert stored.apple_refresh_token is None
        reasons = await kit.db.execute(  # type: ignore[attr-defined]
            select(UserSessionModel.revoked_reason).where(
                UserSessionModel.user_id == user.id
            )
        )
        assert set(reasons.scalars()) == {RevocationReason.APPLE_REVOKED.value}
        [event] = await _events(kit, AuthAction.APPLE_NOTIFICATION)
        assert _details(event)["event"] == "consent-revoked"
        assert _details(event)["sessions_revoked"] == 2

    async def test_account_delete_also_unlinks(self, providers):
        kit = providers.kit
        user = await self._apple_user(providers)

        result = await self._notify(providers, "account-delete", user.apple_sub)

        assert result.unlinked
        assert (await _user(kit, user.id)).apple_sub is None
        [event] = await _events(kit, AuthAction.APPLE_NOTIFICATION)
        assert _details(event)["remaining_methods"] == []

    @pytest.mark.parametrize("event", ["email-disabled", "email-enabled"])
    async def test_email_forwarding_changes_are_only_recorded(self, providers, event):
        kit = providers.kit
        user = await self._apple_user(providers)

        result = await self._notify(providers, event, user.apple_sub)

        assert result.sessions_revoked == 0
        assert len(await kit.sessions.list_active(user.id, kit.clock.now)) == 2
        [recorded] = await _events(kit, AuthAction.APPLE_NOTIFICATION)
        assert recorded.user_id == user.id and _details(recorded)["event"] == event

    async def test_unknown_apple_account_is_recorded_without_user(self, providers):
        result = await self._notify(providers, "consent-revoked", "000999.nadie.0001")

        assert not result.matched
        [event] = await _events(providers.kit, AuthAction.APPLE_NOTIFICATION)
        assert event.user_id is None and _details(event)["matched"] is False

    async def test_forged_notification_is_rejected(self, providers):
        from tests.identity_providers import rsa_key

        forged = providers.apple.sign(
            {
                "iss": "https://appleid.apple.com",
                "aud": "app.lunance.ios",
                "iat": 1,
                "events": json.dumps({"type": "account-delete", "sub": "x"}),
            },
            key=rsa_key(),
        )

        with pytest.raises(InvalidProviderTokenError):
            await providers.notification_handler().handle(
                AppleNotificationCommand(payload=forged)
            )


class TestAccountsWithoutPassword:
    async def test_email_login_is_rejected_like_a_wrong_password(self, providers):
        result = await providers.google_sign_in(
            providers.google.id_token(email="ana@gmail.com")
        )

        with pytest.raises(InvalidCredentialsError):
            await providers.kit.login_handler().handle(
                LoginCommand(
                    email="ana@gmail.com", password=PASSWORD, context=context()
                )
            )
        assert result.user.password is None

    async def test_change_password_asks_to_create_one(self, providers):
        result = await providers.google_sign_in(providers.google.id_token())

        with pytest.raises(PasswordNotSetError):
            await providers.kit.change_handler().handle(
                ChangePasswordCommand(
                    user_id=result.user.id,
                    session_uuid=result.issued.session.uuid,
                    current_password="lo-que-sea",
                    new_password=NEW_PASSWORD,
                )
            )

    async def test_reset_sets_a_first_password(self, providers):
        kit = providers.kit
        await providers.google_sign_in(providers.google.id_token(email="ana@gmail.com"))

        await kit.forgot_handler().handle(
            RequestPasswordResetCommand(email="ana@gmail.com")
        )
        link = kit.queue.to("ana@gmail.com")[-1].text
        token = link.split("token=", 1)[1].split()[0]
        await kit.reset_handler().handle(
            ResetPasswordCommand(token=token, password=NEW_PASSWORD, context=context())
        )
        issued = await kit.login_handler().handle(
            LoginCommand(
                email="ana@gmail.com", password=NEW_PASSWORD, context=context()
            )
        )

        assert issued.access_token

    async def test_register_notice_names_the_provider(self, providers):
        kit = providers.kit
        await providers.google_sign_in(providers.google.id_token(email="ana@gmail.com"))

        await kit.register_handler().handle(
            RegisterCommand(
                email="ana@gmail.com",
                username="ana2",
                password=PASSWORD,
                context=context(),
            )
        )

        [mail] = kit.queue.to("ana@gmail.com")
        assert "inicia sesión con Google" in mail.text


class TestChangeUsername:
    def _handler(self, kit: AuthKit) -> ChangeUsernameHandler:
        return ChangeUsernameHandler(
            user_repository=kit.users,
            pending_signup_repository=kit.pending,
            auth_event_repository=kit.events,
            uow=kit.uow,
            now=kit.clock,
        )

    async def test_renames_and_audits(self, kit):
        user = await kit.create_user(name="usuario_1111")

        renamed = await self._handler(kit).handle(
            ChangeUsernameCommand(user_id=user.id, username="  diego ")
        )

        assert renamed.name == "diego"
        [event] = await _events(kit, AuthAction.USERNAME_CHANGED)
        assert event.details == {"from": "usuario_1111", "to": "diego"}

    async def test_taken_or_reserved_usernames_are_rejected(self, kit):
        await kit.create_user(name="ocupado")
        await kit.register_handler().handle(
            RegisterCommand(
                email="p@example.com",
                username="apartado",
                password=PASSWORD,
                context=context(),
            )
        )
        user_id = await _committed_user(kit)

        for name in ("ocupado", "apartado"):
            with pytest.raises(UsernameAlreadyExistsError):
                await self._handler(kit).handle(
                    ChangeUsernameCommand(user_id=user_id, username=name)
                )
