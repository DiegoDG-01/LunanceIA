import time

from fastapi import HTTPException, Request
from fastapi_advanced_rate_limiter.fixed_window import FixedWindowRateLimiter

from infrastructure.config.settings import settings

limiter_1_per_day = FixedWindowRateLimiter(
    capacity=1, fill_rate=1 / 86400, scope="ip", backend="memory"
)
limiter_2_per_day = FixedWindowRateLimiter(
    capacity=2, fill_rate=2 / 86400, scope="ip", backend="memory"
)
limiter_5_per_hour = FixedWindowRateLimiter(
    capacity=5, fill_rate=5 / 3600, scope="ip", backend="memory"
)
limiter_5_per_minute = FixedWindowRateLimiter(
    capacity=5, fill_rate=5 / 60, scope="ip", backend="memory"
)
limiter_10_per_minute = FixedWindowRateLimiter(
    capacity=10, fill_rate=10 / 60, scope="ip", backend="memory"
)
limiter_15_per_minute = FixedWindowRateLimiter(
    capacity=15, fill_rate=15 / 60, scope="ip", backend="memory"
)
limiter_20_per_minute = FixedWindowRateLimiter(
    capacity=20, fill_rate=20 / 60, scope="ip", backend="memory"
)
limiter_30_per_minute = FixedWindowRateLimiter(
    capacity=30, fill_rate=30 / 60, scope="ip", backend="memory"
)
limiter_50_per_minute = FixedWindowRateLimiter(
    capacity=50, fill_rate=50 / 60, scope="ip", backend="memory"
)
limiter_100_per_minute = FixedWindowRateLimiter(
    capacity=100, fill_rate=100 / 60, scope="ip", backend="memory"
)


def enforce_rate_limit(limiter: FixedWindowRateLimiter, request: Request) -> None:
    if settings.ENVIRONMENT.upper() == "TEST":
        return

    ip = request.client.host if request.client else "unknown"
    key = f"{ip}:{request.url.path}"

    if not limiter.allow_request(key):
        status = limiter.get_status(key)
        window_size = status["window_size"]
        current_window = status["window"]
        wait_time = max(1, int((current_window + 1) * window_size - time.time() + 1))

        if window_size >= 86400:
            unit = "day"
        elif window_size >= 3600:
            unit = "hour"
        else:
            unit = "minute"
        detail_msg = f"Rate limit exceeded: {limiter.capacity} per 1 {unit}"

        raise HTTPException(
            status_code=429,
            detail=detail_msg,
            headers={
                "Retry-After": str(int(wait_time)),
                "X-RateLimit-Remaining": "0",
            },
        )
