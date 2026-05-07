import abc

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.utils.rate_limiter import rate_limiters

logger = structlog.get_logger()


class BaseCollector(abc.ABC):
    """Base class for all data collectors."""

    source_name: str = "unknown"
    rate_limit_name: str = "unknown"

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=True,
                headers={"User-Agent": "CryptoScanMachine/0.1"},
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
    async def fetch(self, url: str, params: dict | None = None) -> dict:
        await rate_limiters.wait_and_acquire(self.rate_limit_name)
        client = await self.get_client()
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    @abc.abstractmethod
    async def collect(self, **kwargs) -> list[dict]:
        pass
