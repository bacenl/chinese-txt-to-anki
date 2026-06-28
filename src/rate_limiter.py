"""Token-bucket rate limiter for provider request scheduling."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass


@dataclass
class RateLimitConfig:
    """Rate limit configuration. requests_per_minute=0 means unlimited."""

    requests_per_minute: float = 0

    def __post_init__(self) -> None:
        if self.requests_per_minute < 0:
            raise ValueError("requests_per_minute cannot be negative")


class TokenBucketRateLimiter:
    """Token bucket rate limiter with burst capacity of 2 tokens."""

    _CAPACITY = 2

    def __init__(self, config: RateLimitConfig) -> None:
        self._rate = config.requests_per_minute / 60.0  # tokens per second
        self._tokens = float(self._CAPACITY)
        self._last_time = time.monotonic()

    async def acquire(self, tokens: int = 1) -> None:
        """Block until a request slot is available."""
        if self._rate == 0:
            return

        while True:
            now = time.monotonic()
            elapsed = now - self._last_time
            self._tokens = min(self._CAPACITY, self._tokens + elapsed * self._rate)
            self._last_time = now

            if self._tokens >= tokens:
                self._tokens -= tokens
                return

            deficit = tokens - self._tokens
            wait_seconds = deficit / self._rate
            await asyncio.sleep(wait_seconds)
