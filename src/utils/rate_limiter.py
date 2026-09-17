"""Concurrency control and adaptive rate limiting with exponential backoff and jitter."""
import asyncio
import random
import time
from typing import Optional


class AsyncRateLimiter:
    """Token bucket / leaky rate limiter with concurrency semaphore."""

    def __init__(self, requests_per_second: float = 5.0, max_concurrency: int = 5):
        self.requests_per_second = max(0.1, requests_per_second)
        self.interval = 1.0 / self.requests_per_second
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self._last_request_time = 0.0
        self._lock = asyncio.Lock()
        self._cooldown_until = 0.0

    async def acquire(self) -> None:
        """Wait for concurrency slot and adhere to rate limits."""
        await self.semaphore.acquire()
        async with self._lock:
            now = time.monotonic()

            # Respect global cooldown if triggered by 429/FloodWait
            if now < self._cooldown_until:
                wait_time = self._cooldown_until - now
                await asyncio.sleep(wait_time)
                now = time.monotonic()

            elapsed = now - self._last_request_time
            if elapsed < self.interval:
                sleep_needed = self.interval - elapsed
                await asyncio.sleep(sleep_needed)
            self._last_request_time = time.monotonic()

    def release(self) -> None:
        """Release concurrency slot."""
        self.semaphore.release()

    def apply_cooldown(self, seconds: float) -> None:
        """Enforce platform-wide cooldown upon receiving 429 / FloodWait."""
        self._cooldown_until = max(self._cooldown_until, time.monotonic() + seconds)

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.release()


async def retry_with_backoff(
    coro_func,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    factor: float = 2.0,
    jitter: bool = True
):
    """Execute coroutine with exponential backoff and jitter."""
    delay = initial_delay
    last_exception: Optional[Exception] = None

    for attempt in range(max_retries):
        try:
            return await coro_func()
        except Exception as exc:
            last_exception = exc
            if attempt == max_retries - 1:
                raise exc

            # Calculate sleep with optional jitter
            sleep_duration = min(max_delay, delay)
            if jitter:
                sleep_duration = sleep_duration * (0.5 + random.random())

            await asyncio.sleep(sleep_duration)
            delay *= factor

    if last_exception:
        raise last_exception
