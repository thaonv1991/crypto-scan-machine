import asyncio
import time

import structlog

logger = structlog.get_logger()


class RateLimiter:
    """Token bucket rate limiter for API calls."""

    def __init__(self, calls_per_minute: int, calls_per_day: int | None = None):
        self.calls_per_minute = calls_per_minute
        self.calls_per_day = calls_per_day

        self._minute_tokens = calls_per_minute
        self._day_tokens = calls_per_day
        self._last_minute_refill = time.monotonic()
        self._last_day_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        async with self._lock:
            now = time.monotonic()

            # Refill minute tokens
            elapsed_minutes = (now - self._last_minute_refill) / 60.0
            if elapsed_minutes >= 1.0:
                self._minute_tokens = self.calls_per_minute
                self._last_minute_refill = now

            # Refill day tokens
            if self._day_tokens is not None:
                elapsed_days = (now - self._last_day_refill) / 86400.0
                if elapsed_days >= 1.0:
                    self._day_tokens = self.calls_per_day
                    self._last_day_refill = now

            # Check limits
            if self._minute_tokens <= 0:
                return False
            if self._day_tokens is not None and self._day_tokens <= 0:
                return False

            self._minute_tokens -= 1
            if self._day_tokens is not None:
                self._day_tokens -= 1

            return True

    async def wait_and_acquire(self) -> None:
        while not await self.acquire():
            await asyncio.sleep(1.0)


class RateLimiterRegistry:
    """Registry of rate limiters for different API sources."""

    def __init__(self):
        self._limiters: dict[str, RateLimiter] = {}

    def register(self, name: str, calls_per_minute: int, calls_per_day: int | None = None) -> None:
        self._limiters[name] = RateLimiter(calls_per_minute, calls_per_day)
        logger.info("rate_limiter.registered", name=name, rpm=calls_per_minute, rpd=calls_per_day)

    def get(self, name: str) -> RateLimiter | None:
        return self._limiters.get(name)

    async def acquire(self, name: str) -> bool:
        limiter = self._limiters.get(name)
        if limiter is None:
            return True
        return await limiter.acquire()

    async def wait_and_acquire(self, name: str) -> None:
        limiter = self._limiters.get(name)
        if limiter is not None:
            await limiter.wait_and_acquire()


rate_limiters = RateLimiterRegistry()

# Register default rate limiters (free tier limits)
rate_limiters.register("coingecko", calls_per_minute=10, calls_per_day=10000)
rate_limiters.register("dexscreener", calls_per_minute=60)
rate_limiters.register("etherscan", calls_per_minute=5)
rate_limiters.register("bscscan", calls_per_minute=5)
rate_limiters.register("twitter", calls_per_minute=15)
rate_limiters.register("reddit", calls_per_minute=10)
rate_limiters.register("deepseek", calls_per_minute=10)
rate_limiters.register("gemini", calls_per_minute=15)
rate_limiters.register("openai", calls_per_minute=3)
