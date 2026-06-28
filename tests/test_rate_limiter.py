"""Tests for the rate-limit-aware scheduler (Task 2.2)."""

import asyncio
import time

import pytest

from src.rate_limiter import RateLimitConfig, TokenBucketRateLimiter


# ---------------------------------------------------------------------------
# Unlimited mode
# ---------------------------------------------------------------------------


def test_unlimited_rate_limiter_does_not_delay():
    config = RateLimitConfig(requests_per_minute=0)
    limiter = TokenBucketRateLimiter(config)

    start = time.monotonic()
    for _ in range(20):
        asyncio.run(limiter.acquire())
    elapsed = time.monotonic() - start

    # 20 unlimited acquires should complete well under 0.1s
    assert elapsed < 0.1


# ---------------------------------------------------------------------------
# Throttling
# ---------------------------------------------------------------------------


def test_rate_limiter_throttles_when_bucket_is_empty():
    """After exhausting burst capacity, the next acquire must wait."""
    # 3 600 req/min = 60/s → one token every ~17ms; bucket capacity = 2
    config = RateLimitConfig(requests_per_minute=3600)
    limiter = TokenBucketRateLimiter(config)

    # Drain both initial tokens to empty the bucket
    asyncio.run(limiter.acquire())
    asyncio.run(limiter.acquire())

    start = time.monotonic()
    asyncio.run(limiter.acquire())  # must wait for refill
    elapsed = time.monotonic() - start

    # Should have waited at least half the token interval (8ms)
    assert elapsed >= 0.008


def test_rate_limiter_allows_burst_then_throttles():
    """Tokens accumulate up to max capacity; burst is allowed, then slows down."""
    # 600 req/min = 10/s → one token every 100ms; capacity = 2
    config = RateLimitConfig(requests_per_minute=600)
    limiter = TokenBucketRateLimiter(config)

    # First two should be near-instant (burst)
    start = time.monotonic()
    asyncio.run(limiter.acquire())
    asyncio.run(limiter.acquire())
    burst_elapsed = time.monotonic() - start
    assert burst_elapsed < 0.05

    # Third must wait for refill (~100ms)
    start = time.monotonic()
    asyncio.run(limiter.acquire())
    wait_elapsed = time.monotonic() - start
    assert wait_elapsed >= 0.05


# ---------------------------------------------------------------------------
# RateLimitConfig validation
# ---------------------------------------------------------------------------


def test_rate_limit_config_zero_means_unlimited():
    config = RateLimitConfig(requests_per_minute=0)
    assert config.requests_per_minute == 0


def test_rate_limit_config_negative_raises():
    with pytest.raises((ValueError, TypeError)):
        RateLimitConfig(requests_per_minute=-1)


def test_rate_limit_config_default_is_unlimited():
    config = RateLimitConfig()
    assert config.requests_per_minute == 0


# ---------------------------------------------------------------------------
# Acquire is async-safe
# ---------------------------------------------------------------------------


def test_rate_limiter_acquire_is_awaitable():
    config = RateLimitConfig(requests_per_minute=0)
    limiter = TokenBucketRateLimiter(config)
    import inspect

    coro = limiter.acquire()
    assert inspect.isawaitable(coro)
    asyncio.run(coro)
