"""Unit tests for the UserSession entity (duración web vs mobile, inactividad y tope)."""

from datetime import UTC, datetime, timedelta

import pytest

from domain.entities.auth.session import (
    Platform,
    RevocationReason,
    SessionLifetime,
    UserSession,
)

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
WEB = SessionLifetime(idle=timedelta(days=1), absolute=timedelta(days=7))
MOBILE = SessionLifetime(idle=timedelta(days=30), absolute=timedelta(days=90))


def _open(platform: Platform = Platform.WEB, lifetime: SessionLifetime = WEB) -> UserSession:
    return UserSession.open(
        user_id=1,
        device_id="0b5f3c55-7f4e-4f0e-9a43-0d6c2d0d6b8e",
        platform=platform,
        lifetime=lifetime,
        now=NOW,
        ip="203.0.113.5",
    )


@pytest.mark.unit
class TestUserSession:
    def test_open_web_session_uses_web_lifetime(self):
        session = _open()

        assert session.idle_expires_at == NOW + timedelta(days=1)
        assert session.absolute_expires_at == NOW + timedelta(days=7)
        assert session.created_ip == session.last_ip == "203.0.113.5"
        assert session.is_active(NOW)

    def test_open_mobile_session_uses_mobile_lifetime(self):
        session = _open(Platform.IOS, MOBILE)

        assert session.idle_expires_at == NOW + timedelta(days=30)
        assert session.absolute_expires_at == NOW + timedelta(days=90)

    def test_idle_never_exceeds_absolute(self):
        session = _open(lifetime=SessionLifetime(timedelta(days=10), timedelta(days=2)))

        assert session.idle_expires_at == session.absolute_expires_at

    def test_inactive_after_idle_timeout(self):
        session = _open()

        assert not session.is_active(NOW + timedelta(days=1, seconds=1))

    def test_touch_renews_idle_and_records_ip(self):
        session = _open()
        later = NOW + timedelta(hours=20)

        session.touch(later, WEB.idle, "198.51.100.9")

        assert session.last_seen_at == later
        assert session.idle_expires_at == later + timedelta(days=1)
        assert session.last_ip == "198.51.100.9"
        assert session.is_active(NOW + timedelta(days=1, hours=1))

    def test_touch_never_passes_absolute_limit(self):
        session = _open()
        near_end = NOW + timedelta(days=6, hours=12)

        session.touch(near_end, WEB.idle)

        assert session.idle_expires_at == NOW + timedelta(days=7)
        assert not session.is_active(NOW + timedelta(days=7))

    def test_revoke_is_idempotent(self):
        session = _open()

        session.revoke(NOW, RevocationReason.SIGNED_OUT)
        session.revoke(NOW + timedelta(hours=1), RevocationReason.REFRESH_REUSE)

        assert session.revoked_at == NOW
        assert session.revoked_reason is RevocationReason.SIGNED_OUT
        assert not session.is_active(NOW)

    def test_platform_is_mobile(self):
        assert not Platform.WEB.is_mobile
        assert Platform.IOS.is_mobile
        assert Platform.ANDROID.is_mobile
