"""Handlers de sesión contra repositorios reales (SQLite) y Redis falso: login, rotación del
refresh, margen de gracia, reuso, reemplazo por dispositivo, logout, revocación y purga."""

from datetime import timedelta

import bcrypt
import pytest
from sqlalchemy import select

from application.auth.commands.login import LoginCommand
from application.auth.commands.logout import LogoutCommand
from application.auth.commands.refresh_session import RefreshSessionCommand
from application.auth.commands.revoke_session import RevokeSessionCommand
from application.auth.queries.list_sessions import ListSessionsQuery
from domain.entities.auth.auth_event import AuthAction, AuthEvent
from domain.entities.auth.session import Platform, RevocationReason
from infrastructure.cache.session_revocations import PersistentSessionRevocations
from infrastructure.database.models.auth_event import AuthEventModel
from infrastructure.database.models.refresh_token import RefreshTokenModel
from infrastructure.database.models.user import UserModel
from infrastructure.database.models.user_session import UserSessionModel
from shared.exceptions.domain import (
    InvalidCredentialsError,
    SessionExpiredError,
    SessionNotFoundError,
    UserInactiveError,
)
from shared.utils.tokens import hash_token, refresh_successor

from .conftest import PASSWORD, AuthKit, BrokenRedis, context

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


async def _events(kit: AuthKit, action: AuthAction) -> list[AuthEventModel]:
    result = await kit.db.execute(  # type: ignore[attr-defined]
        select(AuthEventModel).where(AuthEventModel.action == action.value)
    )
    return list(result.scalars().all())


def _details(event: AuthEventModel) -> dict:
    return event.details or {}


class TestLogin:
    async def test_web_login_opens_session_with_web_lifetime(self, kit: AuthKit):
        user = await kit.create_user()
        ctx = context()

        issued = await kit.login(user, ctx)

        session = issued.session
        assert session.platform is Platform.WEB
        assert session.device_id == ctx.device_id
        assert session.idle_expires_at == kit.clock.now + timedelta(days=1)
        assert session.absolute_expires_at == kit.clock.now + timedelta(days=7)
        assert issued.refresh_token.startswith("rt_")
        claims = kit.issuer.verify(issued.access_token)
        assert claims.user_uuid == user.uuid
        assert claims.session_uuid == session.uuid

        stored = await kit.tokens.get(hash_token(issued.refresh_token))
        assert stored is not None and stored.session_id == session.id

    async def test_mobile_login_uses_mobile_lifetime(self, kit: AuthKit):
        user = await kit.create_user()

        issued = await kit.login(user, context(platform=Platform.ANDROID))

        assert issued.session.idle_expires_at == kit.clock.now + timedelta(days=30)
        assert issued.session.absolute_expires_at == kit.clock.now + timedelta(days=90)

    async def test_login_updates_last_login_and_records_event(self, kit: AuthKit):
        user = await kit.create_user()

        issued = await kit.login(user, context())

        refreshed = await kit.users.get_by_id(user.id)
        assert refreshed is not None
        assert refreshed.last_login.replace(tzinfo=None) == kit.clock.now.replace(
            tzinfo=None
        )
        [event] = await _events(kit, AuthAction.LOGIN_SUCCEEDED)
        assert event.user_id == user.id
        assert event.session_id == issued.session.id
        assert event.ip == "203.0.113.5"
        assert PASSWORD not in str(event.details)
        assert issued.refresh_token not in str(event.details)

    async def test_same_device_replaces_only_that_session(self, kit: AuthKit):
        user = await kit.create_user()
        phone, laptop = context(platform=Platform.IOS), context()
        first = await kit.login(user, phone)
        other = await kit.login(user, laptop)

        second = await kit.login(user, phone)

        active = await kit.sessions.list_active(user.id, kit.clock.now)
        assert {s.uuid for s in active} == {second.session.uuid, other.session.uuid}
        old = await kit.sessions.get(first.session.id)  # type: ignore[arg-type]
        assert old is not None
        assert old.revoked_reason is RevocationReason.REPLACED
        # El access token de la sesión sustituida deja de valer al instante.
        assert await kit.redis.exists(f"revoked_sid:{first.session.uuid}")  # type: ignore[attr-defined]
        assert await kit.revocations.is_revoked(first.session.uuid)
        assert not await kit.revocations.is_revoked(other.session.uuid)
        [revoked] = await _events(kit, AuthAction.SESSION_REVOKED)
        assert _details(revoked)["reason"] == "replaced"
        assert _details(revoked)["revoked_by"] == "system"

    async def test_wrong_password_records_failure_with_username(self, kit: AuthKit):
        user = await kit.create_user()

        with pytest.raises(InvalidCredentialsError):
            await kit.login_handler().handle(
                LoginCommand(username=user.name, password="Wrong-pass1", context=context())
            )

        [event] = await _events(kit, AuthAction.LOGIN_FAILED)
        assert event.user_id == user.id
        assert event.details == {"username": user.name, "reason": "invalid_credentials"}
        assert await kit.sessions.list_active(user.id, kit.clock.now) == []

    async def test_unknown_user_records_failure_without_user(self, kit: AuthKit):
        with pytest.raises(InvalidCredentialsError):
            await kit.login_handler().handle(
                LoginCommand(username="ghost", password=PASSWORD, context=context())
            )

        [event] = await _events(kit, AuthAction.LOGIN_FAILED)
        assert event.user_id is None
        assert _details(event)["username"] == "ghost"

    async def test_inactive_user_is_rejected_after_password_check(self, kit: AuthKit):
        user = await kit.create_user(is_active=False)

        with pytest.raises(UserInactiveError):
            await kit.login(user, context())

        [event] = await _events(kit, AuthAction.LOGIN_FAILED)
        assert _details(event)["reason"] == "inactive"

    async def test_bcrypt_hash_is_rehashed_to_argon2_on_login(self, kit: AuthKit):
        legacy = bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt(rounds=4)).decode()
        user = await kit.create_user(password_hash=legacy)

        await kit.login(user, context())

        model = await kit.db.get(UserModel, user.id)  # type: ignore[attr-defined]
        assert model.password.startswith("$argon2id$")
        assert await kit.hasher.verify(PASSWORD, model.password)
        # La contraseña sigue funcionando con el hash nuevo.
        await kit.login(user, context())

    async def test_bcrypt_hash_is_kept_when_password_is_wrong(self, kit: AuthKit):
        legacy = bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt(rounds=4)).decode()
        user = await kit.create_user(password_hash=legacy)

        with pytest.raises(InvalidCredentialsError):
            await kit.login_handler().handle(
                LoginCommand(username=user.name, password="Wrong-pass1", context=context())
            )

        model = await kit.db.get(UserModel, user.id)  # type: ignore[attr-defined]
        assert model.password == legacy


class TestRefresh:
    async def test_refresh_rotates_to_single_successor(self, kit: AuthKit):
        user = await kit.create_user()
        ctx = context()
        issued = await kit.login(user, ctx)
        kit.clock.advance(hours=2)

        refreshed = await kit.refresh_handler().handle(
            RefreshSessionCommand(refresh_token=issued.refresh_token, context=ctx)
        )

        assert refreshed.refresh_token == refresh_successor(
            issued.refresh_token, key=kit.config.refresh_rotation_key
        )
        old = await kit.tokens.get(hash_token(issued.refresh_token))
        assert old is not None and old.rotated_at is not None
        assert refreshed.session.uuid == issued.session.uuid
        assert refreshed.session.last_seen_at == kit.clock.now
        assert refreshed.session.idle_expires_at == kit.clock.now + timedelta(days=1)
        # Un refresh normal no crea eventos de auditoría.
        assert await _events(kit, AuthAction.SESSION_REVOKED) == []
        assert await _events(kit, AuthAction.SESSION_REFRESH_REUSE_DETECTED) == []

    async def test_refresh_updates_last_ip(self, kit: AuthKit):
        user = await kit.create_user()
        ctx = context()
        issued = await kit.login(user, ctx)
        moved = context(device_id=ctx.device_id, ip="198.51.100.77")

        refreshed = await kit.refresh_handler().handle(
            RefreshSessionCommand(refresh_token=issued.refresh_token, context=moved)
        )

        assert refreshed.session.last_ip == "198.51.100.77"
        assert refreshed.session.created_ip == "203.0.113.5"

    async def test_retry_within_grace_returns_same_successor(self, kit: AuthKit):
        user = await kit.create_user()
        ctx = context()
        issued = await kit.login(user, ctx)
        first = await kit.refresh_handler().handle(
            RefreshSessionCommand(refresh_token=issued.refresh_token, context=ctx)
        )
        kit.clock.advance(seconds=10)

        retry = await kit.refresh_handler().handle(
            RefreshSessionCommand(refresh_token=issued.refresh_token, context=ctx)
        )

        assert retry.refresh_token == first.refresh_token
        tokens = (
            await kit.db.execute(  # type: ignore[attr-defined]
                select(RefreshTokenModel).where(
                    RefreshTokenModel.session_id == issued.session.id
                )
            )
        ).scalars().all()
        assert len(tokens) == 2  # sin ramas: el original y su único sucesor
        session = await kit.sessions.get(issued.session.id)  # type: ignore[arg-type]
        assert session is not None and session.revoked_at is None
        # El sucesor sigue sirviendo.
        await kit.refresh_handler().handle(
            RefreshSessionCommand(refresh_token=retry.refresh_token, context=ctx)
        )

    async def test_reuse_outside_grace_revokes_session(self, kit: AuthKit):
        user = await kit.create_user()
        ctx = context()
        issued = await kit.login(user, ctx)
        rotated = await kit.refresh_handler().handle(
            RefreshSessionCommand(refresh_token=issued.refresh_token, context=ctx)
        )
        kit.clock.advance(seconds=31)

        with pytest.raises(SessionExpiredError):
            await kit.refresh_handler().handle(
                RefreshSessionCommand(refresh_token=issued.refresh_token, context=ctx)
            )

        session = await kit.sessions.get(issued.session.id)  # type: ignore[arg-type]
        assert session is not None
        assert session.revoked_reason is RevocationReason.REFRESH_REUSE
        assert await kit.revocations.is_revoked(session.uuid)
        [reuse] = await _events(kit, AuthAction.SESSION_REFRESH_REUSE_DETECTED)
        assert reuse.session_id == session.id
        [revoked] = await _events(kit, AuthAction.SESSION_REVOKED)
        assert _details(revoked)["reason"] == "refresh_reuse"
        # El sucesor legítimo también queda inutilizado: la sesión entera se cerró.
        with pytest.raises(SessionExpiredError):
            await kit.refresh_handler().handle(
                RefreshSessionCommand(refresh_token=rotated.refresh_token, context=ctx)
            )

    async def test_retry_after_successor_rotated_is_rejected(self, kit: AuthKit):
        user = await kit.create_user()
        ctx = context()
        issued = await kit.login(user, ctx)
        first = await kit.refresh_handler().handle(
            RefreshSessionCommand(refresh_token=issued.refresh_token, context=ctx)
        )
        await kit.refresh_handler().handle(
            RefreshSessionCommand(refresh_token=first.refresh_token, context=ctx)
        )

        with pytest.raises(SessionExpiredError):
            await kit.refresh_handler().handle(
                RefreshSessionCommand(refresh_token=issued.refresh_token, context=ctx)
            )

    async def test_unknown_token_is_rejected(self, kit: AuthKit):
        with pytest.raises(SessionExpiredError):
            await kit.refresh_handler().handle(
                RefreshSessionCommand(refresh_token="rt_nope", context=context())
            )

    async def test_refresh_from_another_device_is_rejected(self, kit: AuthKit):
        user = await kit.create_user()
        issued = await kit.login(user, context())

        with pytest.raises(SessionExpiredError):
            await kit.refresh_handler().handle(
                RefreshSessionCommand(refresh_token=issued.refresh_token, context=context())
            )

    async def test_refresh_from_another_platform_is_rejected(self, kit: AuthKit):
        user = await kit.create_user()
        ctx = context()
        issued = await kit.login(user, ctx)

        with pytest.raises(SessionExpiredError):
            await kit.refresh_handler().handle(
                RefreshSessionCommand(
                    refresh_token=issued.refresh_token,
                    context=context(device_id=ctx.device_id, platform=Platform.IOS),
                )
            )

    async def test_web_session_expires_after_one_idle_day(self, kit: AuthKit):
        user = await kit.create_user()
        ctx = context()
        issued = await kit.login(user, ctx)
        kit.clock.advance(days=1, seconds=1)

        with pytest.raises(SessionExpiredError):
            await kit.refresh_handler().handle(
                RefreshSessionCommand(refresh_token=issued.refresh_token, context=ctx)
            )

    async def test_mobile_session_survives_idle_day(self, kit: AuthKit):
        user = await kit.create_user()
        ctx = context(platform=Platform.IOS)
        issued = await kit.login(user, ctx)
        kit.clock.advance(days=20)

        refreshed = await kit.refresh_handler().handle(
            RefreshSessionCommand(refresh_token=issued.refresh_token, context=ctx)
        )

        assert refreshed.session.idle_expires_at == kit.clock.now + timedelta(days=30)

    async def test_refresh_never_extends_past_absolute_limit(self, kit: AuthKit):
        user = await kit.create_user()
        ctx = context()
        issued = await kit.login(user, ctx)
        token = issued.refresh_token
        for _ in range(7):  # un refresh al día: la inactividad nunca vence
            kit.clock.advance(hours=23)
            token = (
                await kit.refresh_handler().handle(
                    RefreshSessionCommand(refresh_token=token, context=ctx)
                )
            ).refresh_token
        session = await kit.sessions.get(issued.session.id)  # type: ignore[arg-type]
        assert session is not None
        assert session.idle_expires_at == session.absolute_expires_at
        kit.clock.now = session.absolute_expires_at

        with pytest.raises(SessionExpiredError):
            await kit.refresh_handler().handle(
                RefreshSessionCommand(refresh_token=token, context=ctx)
            )

    async def test_inactive_user_cannot_refresh(self, kit: AuthKit):
        user = await kit.create_user()
        ctx = context()
        issued = await kit.login(user, ctx)
        user.is_active = False
        await kit.db.flush()  # type: ignore[attr-defined]

        with pytest.raises(SessionExpiredError):
            await kit.refresh_handler().handle(
                RefreshSessionCommand(refresh_token=issued.refresh_token, context=ctx)
            )


class TestLogout:
    async def test_logout_closes_only_current_session(self, kit: AuthKit):
        user = await kit.create_user()
        current = await kit.login(user, context())
        other = await kit.login(user, context(platform=Platform.IOS))

        result = await kit.logout_handler().handle(
            LogoutCommand(refresh_token=current.refresh_token, context=context())
        )

        assert result.revoked == 1
        assert await kit.revocations.is_revoked(current.session.uuid)
        assert not await kit.revocations.is_revoked(other.session.uuid)
        [event] = await _events(kit, AuthAction.SESSION_REVOKED)
        assert _details(event)["reason"] == "signed_out"
        assert _details(event)["revoked_by"] == "user"

    async def test_logout_all_devices(self, kit: AuthKit):
        user = await kit.create_user()
        current = await kit.login(user, context())
        other = await kit.login(user, context(platform=Platform.ANDROID))

        result = await kit.logout_handler().handle(
            LogoutCommand(
                refresh_token=current.refresh_token, all_devices=True, context=context()
            )
        )

        assert result.revoked == 2
        assert await kit.sessions.list_active(user.id, kit.clock.now) == []
        assert await kit.revocations.is_revoked(other.session.uuid)
        events = await _events(kit, AuthAction.SESSION_REVOKED)
        assert {_details(e)["reason"] for e in events} == {"signed_out_everywhere"}
        assert {_details(e)["actor_session_uuid"] for e in events} == {
            current.session.uuid
        }

    async def test_rotated_token_cannot_sign_out_other_devices(self, kit: AuthKit):
        user = await kit.create_user()
        ctx = context()
        current = await kit.login(user, ctx)
        other = await kit.login(user, context(platform=Platform.IOS))
        await kit.refresh_handler().handle(
            RefreshSessionCommand(refresh_token=current.refresh_token, context=ctx)
        )

        result = await kit.logout_handler().handle(
            LogoutCommand(
                refresh_token=current.refresh_token, all_devices=True, context=ctx
            )
        )

        assert result.revoked == 1
        assert not await kit.revocations.is_revoked(other.session.uuid)

    async def test_logout_with_unknown_token_is_a_no_op(self, kit: AuthKit):
        result = await kit.logout_handler().handle(
            LogoutCommand(refresh_token="rt_unknown", context=context())
        )

        assert result.revoked == 0


class TestRevokeAndList:
    async def test_list_marks_current_session(self, kit: AuthKit):
        user = await kit.create_user()
        web = await kit.login(user, context())
        kit.clock.advance(minutes=1)
        phone = await kit.login(user, context(platform=Platform.IOS))

        views = await kit.list_handler().handle(
            ListSessionsQuery(user_id=user.id, current_session_uuid=web.session.uuid)
        )

        assert [v.session.uuid for v in views] == [phone.session.uuid, web.session.uuid]
        assert [v.is_current for v in views] == [False, True]

    async def test_revoke_own_session(self, kit: AuthKit):
        user = await kit.create_user()
        web = await kit.login(user, context())
        phone = await kit.login(user, context(platform=Platform.IOS))

        await kit.revoke_handler().handle(
            RevokeSessionCommand(
                user_id=user.id,
                session_uuid=phone.session.uuid,
                actor_session_uuid=web.session.uuid,
            )
        )

        assert await kit.revocations.is_revoked(phone.session.uuid)
        [event] = await _events(kit, AuthAction.SESSION_REVOKED)
        assert event.details == {
            "session_uuid": phone.session.uuid,
            "reason": "revoked_by_user",
            "revoked_by": "user",
            "actor_session_uuid": web.session.uuid,
        }
        # Su refresh token tampoco sirve ya.
        with pytest.raises(SessionExpiredError):
            await kit.refresh_handler().handle(
                RefreshSessionCommand(
                    refresh_token=phone.refresh_token,
                    context=context(
                        device_id=phone.session.device_id, platform=Platform.IOS
                    ),
                )
            )

    async def test_cannot_revoke_another_users_session(self, kit: AuthKit):
        owner, intruder = await kit.create_user(), await kit.create_user()
        issued = await kit.login(owner, context())

        with pytest.raises(SessionNotFoundError):
            await kit.revoke_handler().handle(
                RevokeSessionCommand(user_id=intruder.id, session_uuid=issued.session.uuid)
            )

        assert not await kit.revocations.is_revoked(issued.session.uuid)

    async def test_revoke_unknown_session_is_not_found(self, kit: AuthKit):
        user = await kit.create_user()

        with pytest.raises(SessionNotFoundError):
            await kit.revoke_handler().handle(
                RevokeSessionCommand(
                    user_id=user.id, session_uuid="00000000-0000-0000-0000-000000000000"
                )
            )


class TestImmediateRevocation:
    async def test_database_is_authority_when_redis_is_down(self, kit: AuthKit):
        user = await kit.create_user()
        active = await kit.login(user, context())
        closed = await kit.login(user, context())
        await kit.logout_handler().handle(
            LogoutCommand(refresh_token=closed.refresh_token, context=context())
        )
        down = PersistentSessionRevocations(
            BrokenRedis,  # type: ignore[arg-type]
            ttl_seconds=600,
            session_repository=kit.sessions,
            now=kit.clock,
        )

        assert await down.is_revoked(closed.session.uuid)
        assert not await down.is_revoked(active.session.uuid)
        assert await down.is_revoked("00000000-0000-0000-0000-000000000000")

    async def test_database_catches_revocation_missing_from_redis(self, kit: AuthKit):
        user = await kit.create_user()
        issued = await kit.login(user, context())
        await kit.logout_handler().handle(
            LogoutCommand(refresh_token=issued.refresh_token, context=context())
        )
        await kit.redis.flushall()  # type: ignore[attr-defined]  # Redis reiniciado

        assert await kit.revocations.is_revoked(issued.session.uuid)

    async def test_revoke_survives_redis_outage(self, kit: AuthKit):
        user = await kit.create_user()
        issued = await kit.login(user, context())
        kit.revocations = PersistentSessionRevocations(
            BrokenRedis,  # type: ignore[arg-type]
            ttl_seconds=600,
            session_repository=kit.sessions,
            now=kit.clock,
        )

        await kit.logout_handler().handle(
            LogoutCommand(refresh_token=issued.refresh_token, context=context())
        )

        assert await kit.revocations.is_revoked(issued.session.uuid)

    async def test_redis_entry_expires_with_access_token(self, kit: AuthKit):
        user = await kit.create_user()
        issued = await kit.login(user, context())
        await kit.logout_handler().handle(
            LogoutCommand(refresh_token=issued.refresh_token, context=context())
        )

        ttl = await kit.redis.ttl(f"revoked_sid:{issued.session.uuid}")  # type: ignore[attr-defined]
        assert 0 < ttl <= kit.issuer.ttl_seconds


class TestPurge:
    async def test_purges_old_sessions_tokens_and_events(self, kit: AuthKit):
        user = await kit.create_user()
        old = await kit.login(user, context())
        await kit.logout_handler().handle(
            LogoutCommand(refresh_token=old.refresh_token, context=context())
        )
        await kit.events.record(
            AuthEvent(action=AuthAction.LOGIN_FAILED, created_at=kit.clock.now)
        )
        kit.clock.advance(days=31)
        recent = await kit.login(user, context())

        result = await kit.purge_handler().handle()

        assert result.sessions == 1
        remaining = (
            await kit.db.execute(select(UserSessionModel.uuid))  # type: ignore[attr-defined]
        ).scalars().all()
        assert remaining == [recent.session.uuid]
        tokens = (
            await kit.db.execute(select(RefreshTokenModel.session_id))  # type: ignore[attr-defined]
        ).scalars().all()
        assert set(tokens) == {recent.session.id}
        # Los eventos de hace 31 días se quedan (se borran a los 90).
        assert result.events == 0
        kit.clock.advance(days=60)
        assert (await kit.purge_handler().handle()).events >= 3

    async def test_keeps_recently_revoked_sessions(self, kit: AuthKit):
        user = await kit.create_user()
        issued = await kit.login(user, context())
        await kit.logout_handler().handle(
            LogoutCommand(refresh_token=issued.refresh_token, context=context())
        )
        kit.clock.advance(days=29)

        assert (await kit.purge_handler().handle()).sessions == 0
