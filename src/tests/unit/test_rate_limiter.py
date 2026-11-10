from types import SimpleNamespace
from typing import Any

import pytest
from fakeredis import FakeAsyncRedis
from fastapi import HTTPException
from redis.exceptions import ConnectionError as RedisConnectionError

import infrastructure.rate_limiting.client_ip as client_ip_mod
import infrastructure.rate_limiting.limiters as limiters_mod
from infrastructure.cache.redis import set_redis
from infrastructure.rate_limiting.client_ip import client_ip, ip_identity
from infrastructure.rate_limiting.limiters import (
    RateLimiterUnavailable,
    RateLimitRule,
    RedisRateLimiter,
    enforce_rate_limit,
)


class Clock:
    def __init__(self, now: float = 1_000_000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


def _request(
    ip="203.0.113.7", path="/api/v2/accounts", headers=None, rate_limit_id=None
) -> Any:
    state = SimpleNamespace()
    if rate_limit_id is not None:
        state.rate_limit_id = rate_limit_id
    return SimpleNamespace(
        client=SimpleNamespace(host=ip),
        url=SimpleNamespace(path=path),
        headers=headers or {},
        state=state,
    )


class _BrokenRedis:
    def pipeline(self, transaction=True):
        raise RedisConnectionError("down")


def BrokenRedis() -> Any:
    return _BrokenRedis()


@pytest.fixture
def redis():
    client = FakeAsyncRedis(decode_responses=True)
    set_redis(client)
    yield client
    set_redis(None)


@pytest.fixture
def not_test_env(monkeypatch):
    # enforce_rate_limit no hace nada con ENVIRONMENT=TEST.
    monkeypatch.setattr(limiters_mod, "settings", SimpleNamespace(ENVIRONMENT="DEV"))


@pytest.mark.asyncio
class TestRedisRateLimiter:
    async def test_allows_exactly_the_limit_per_window(self, redis):
        limiter = RedisRateLimiter(lambda: redis, clock=Clock())
        rule = RateLimitRule(limit=10, window_seconds=60)

        decisions = [await limiter.hit("k", rule) for _ in range(11)]

        assert all(d.allowed for d in decisions[:10])
        assert decisions[9].remaining == 0
        assert not decisions[10].allowed

    async def test_retry_after_points_to_the_next_window(self, redis):
        clock = Clock(now=60 * 1000 + 45)  # 45 s dentro de la ventana
        limiter = RedisRateLimiter(lambda: redis, clock=clock)
        rule = RateLimitRule(limit=1, window_seconds=60)

        await limiter.hit("k", rule)
        decision = await limiter.hit("k", rule)

        assert not decision.allowed
        assert decision.retry_after == 15

    async def test_counter_resets_in_the_next_window(self, redis):
        clock = Clock()
        limiter = RedisRateLimiter(lambda: redis, clock=clock)
        rule = RateLimitRule(limit=1, window_seconds=60)

        assert (await limiter.hit("k", rule)).allowed
        assert not (await limiter.hit("k", rule)).allowed
        clock.now += 60
        assert (await limiter.hit("k", rule)).allowed

    async def test_rules_and_keys_do_not_share_counters(self, redis):
        limiter = RedisRateLimiter(lambda: redis, clock=Clock())
        per_minute = RateLimitRule(limit=1, window_seconds=60)
        per_hour = RateLimitRule(limit=1, window_seconds=3600)

        assert (await limiter.hit("a", per_minute)).allowed
        assert (await limiter.hit("a", per_hour)).allowed
        assert (await limiter.hit("b", per_minute)).allowed

    async def test_sets_expiry_on_the_window_key(self, redis):
        limiter = RedisRateLimiter(lambda: redis, clock=Clock())
        await limiter.hit("k", RateLimitRule(limit=5, window_seconds=60))

        keys = await redis.keys("rl:*")
        assert len(keys) == 1
        assert 0 < await redis.ttl(keys[0]) <= 60

    async def test_redis_error_raises_unavailable(self):
        limiter = RedisRateLimiter(lambda: BrokenRedis())
        with pytest.raises(RateLimiterUnavailable):
            await limiter.hit("k", RateLimitRule(limit=1, window_seconds=60))


class TestRateLimitRule:
    def test_description_matches_previous_messages(self):
        assert RateLimitRule(10, 60).description == "10 per 1 minute"
        assert RateLimitRule(5, 3600).description == "5 per 1 hour"
        assert RateLimitRule(1, 86400).description == "1 per 1 day"

    def test_rejects_non_positive_values(self):
        with pytest.raises(ValueError):
            RateLimitRule(0, 60)


@pytest.mark.asyncio
class TestEnforceRateLimit:
    async def test_skipped_in_test_environment(self, redis):
        rule = RateLimitRule(limit=1, window_seconds=60)
        for _ in range(3):
            await enforce_rate_limit(rule, _request())

    async def test_raises_429_with_retry_after(self, redis, not_test_env):
        rule = RateLimitRule(limit=2, window_seconds=60)
        request = _request()
        await enforce_rate_limit(rule, request)
        await enforce_rate_limit(rule, request)

        with pytest.raises(HTTPException) as exc_info:
            await enforce_rate_limit(rule, request)

        assert exc_info.value.status_code == 429
        assert exc_info.value.detail == "Rate limit exceeded: 2 per 1 minute"
        headers = exc_info.value.headers
        assert headers is not None
        assert int(headers["Retry-After"]) >= 1
        assert headers["X-RateLimit-Remaining"] == "0"

    async def test_counts_per_path(self, redis, not_test_env):
        rule = RateLimitRule(limit=1, window_seconds=60)
        await enforce_rate_limit(rule, _request(path="/a"))
        await enforce_rate_limit(rule, _request(path="/b"))

    async def test_authenticated_requests_count_per_user_not_ip(self, redis, not_test_env):
        rule = RateLimitRule(limit=1, window_seconds=60)
        # Mismo 127.0.0.1 (MCP), distintos usuarios: no comparten contador.
        await enforce_rate_limit(rule, _request(ip="127.0.0.1", rate_limit_id="user:1"))
        await enforce_rate_limit(rule, _request(ip="127.0.0.1", rate_limit_id="user:2"))
        with pytest.raises(HTTPException):
            await enforce_rate_limit(rule, _request(ip="127.0.0.1", rate_limit_id="user:1"))

    async def test_fails_open_when_redis_is_down(self, not_test_env):
        set_redis(BrokenRedis())
        try:
            await enforce_rate_limit(RateLimitRule(1, 60), _request())
        finally:
            set_redis(None)

    async def test_fails_closed_with_503_when_requested(self, not_test_env):
        set_redis(BrokenRedis())
        try:
            with pytest.raises(HTTPException) as exc_info:
                await enforce_rate_limit(RateLimitRule(1, 60), _request(), fail_closed=True)
        finally:
            set_redis(None)
        assert exc_info.value.status_code == 503
        assert exc_info.value.headers is not None
        assert exc_info.value.headers["Retry-After"] == "5"

    async def test_fails_open_when_redis_was_never_initialized(self, not_test_env):
        set_redis(None)
        await enforce_rate_limit(RateLimitRule(1, 60), _request())


class TestClientIp:
    def test_uses_connection_ip_by_default(self, monkeypatch):
        monkeypatch.setattr(client_ip_mod, "settings", SimpleNamespace(CLIENT_IP_HEADER=""))
        request = _request(ip="10.0.0.1", headers={"CF-Connecting-IP": "198.51.100.1"})
        assert client_ip(request) == "10.0.0.1"

    def test_uses_configured_proxy_header(self, monkeypatch):
        monkeypatch.setattr(
            client_ip_mod, "settings", SimpleNamespace(CLIENT_IP_HEADER="CF-Connecting-IP")
        )
        request = _request(ip="10.0.0.1", headers={"CF-Connecting-IP": "198.51.100.1"})
        assert client_ip(request) == "198.51.100.1"

    def test_falls_back_to_connection_ip_without_header(self, monkeypatch):
        monkeypatch.setattr(
            client_ip_mod, "settings", SimpleNamespace(CLIENT_IP_HEADER="CF-Connecting-IP")
        )
        assert client_ip(_request(ip="10.0.0.1")) == "10.0.0.1"

    def test_ipv6_is_grouped_by_64(self, monkeypatch):
        monkeypatch.setattr(client_ip_mod, "settings", SimpleNamespace(CLIENT_IP_HEADER=""))
        a = ip_identity(_request(ip="2001:db8:1:2::1"))
        b = ip_identity(_request(ip="2001:db8:1:2:ffff::9"))
        c = ip_identity(_request(ip="2001:db8:1:3::1"))
        assert a == b == "ip:2001:db8:1:2::/64"
        assert c != a

    def test_ipv4_mapped_ipv6_counts_as_ipv4(self, monkeypatch):
        monkeypatch.setattr(client_ip_mod, "settings", SimpleNamespace(CLIENT_IP_HEADER=""))
        assert ip_identity(_request(ip="::ffff:203.0.113.7")) == "ip:203.0.113.7"

    def test_unparseable_ip_is_kept_as_is(self, monkeypatch):
        monkeypatch.setattr(client_ip_mod, "settings", SimpleNamespace(CLIENT_IP_HEADER=""))
        assert ip_identity(_request(ip="testclient")) == "ip:testclient"
