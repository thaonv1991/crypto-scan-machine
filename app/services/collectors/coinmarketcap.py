"""
CoinMarketCap Collector - Leading crypto market data provider.
Requires API key for full access. Free tier: 30+ endpoints, 15K calls/mo.
Get API key at: https://pro.coinmarketcap.com/signup
"""

import os

import structlog

from app.services.collectors.base import BaseCollector

logger = structlog.get_logger()

BASE_URL = "https://pro-api.coinmarketcap.com"


class CoinMarketCapCollector(BaseCollector):
    """Collector for CoinMarketCap market data. Requires CMC_API_KEY."""

    source_name = "coinmarketcap"
    rate_limit_name = "coinmarketcap"

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("CMC_API_KEY", "")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def fetch(self, url: str, params: dict | None = None) -> dict:
        if not self.is_configured():
            logger.warning("coinmarketcap.not_configured")
            return {}
        from app.utils.rate_limiter import rate_limiters

        await rate_limiters.wait_and_acquire(self.rate_limit_name)
        client = await self.get_client()
        response = await client.get(
            url,
            params=params,
            headers={"X-CMC_PRO_API_KEY": self.api_key, "Accept": "application/json"},
        )
        response.raise_for_status()
        return response.json()

    async def collect(self, **kwargs) -> list[dict]:
        if not self.is_configured():
            return []
        coins = await self.get_listings_latest()
        return [self.normalize_to_market_data(c) for c in coins]

    async def get_listings_latest(
        self, start: int = 1, limit: int = 100, convert: str = "USD"
    ) -> list[dict]:
        """Get latest crypto listings ranked by market cap."""
        try:
            url = f"{BASE_URL}/v1/cryptocurrency/listings/latest"
            data = await self.fetch(url, params={"start": start, "limit": limit, "convert": convert})
            return data.get("data", [])
        except Exception as e:
            logger.error("coinmarketcap.listings_failed", error=str(e))
            return []

    async def get_quotes_latest(self, ids: str | None = None, slugs: str | None = None) -> dict:
        """Get latest quotes for specific cryptocurrencies."""
        try:
            url = f"{BASE_URL}/v2/cryptocurrency/quotes/latest"
            params = {}
            if ids:
                params["id"] = ids
            elif slugs:
                params["slug"] = slugs
            data = await self.fetch(url, params=params)
            return data.get("data", {})
        except Exception as e:
            logger.error("coinmarketcap.quotes_failed", error=str(e))
            return {}

    async def get_trending_latest(self) -> list[dict]:
        """Get trending cryptocurrencies."""
        try:
            url = f"{BASE_URL}/v1/cryptocurrency/trending/latest"
            data = await self.fetch(url)
            return data.get("data", [])
        except Exception as e:
            logger.error("coinmarketcap.trending_failed", error=str(e))
            return []

    async def get_gainers_losers(self, time_period: str = "24h") -> dict:
        """Get top gainers and losers."""
        try:
            url = f"{BASE_URL}/v1/cryptocurrency/trending/gainers-losers"
            data = await self.fetch(url, params={"time_period": time_period})
            return data.get("data", {})
        except Exception as e:
            logger.error("coinmarketcap.gainers_losers_failed", error=str(e))
            return {}

    async def get_global_metrics(self) -> dict:
        """Get global crypto market metrics."""
        try:
            url = f"{BASE_URL}/v1/global-metrics/quotes/latest"
            data = await self.fetch(url)
            return data.get("data", {})
        except Exception as e:
            logger.error("coinmarketcap.global_metrics_failed", error=str(e))
            return {}

    def normalize_to_market_data(self, coin: dict) -> dict:
        """Normalize CMC coin data to market data format."""
        quote = coin.get("quote", {}).get("USD", {})
        return {
            "name": coin.get("name", ""),
            "symbol": coin.get("symbol", ""),
            "price_usd": quote.get("price"),
            "volume_24h": quote.get("volume_24h"),
            "market_cap": quote.get("market_cap"),
            "fdv": quote.get("fully_diluted_market_cap"),
            "price_change_1h": quote.get("percent_change_1h"),
            "price_change_24h": quote.get("percent_change_24h"),
            "price_change_7d": quote.get("percent_change_7d"),
            "source": "coinmarketcap",
            "extra_data": {
                "cmc_id": coin.get("id"),
                "cmc_rank": coin.get("cmc_rank"),
                "circulating_supply": coin.get("circulating_supply"),
                "total_supply": coin.get("total_supply"),
                "max_supply": coin.get("max_supply"),
                "num_market_pairs": coin.get("num_market_pairs"),
                "date_added": coin.get("date_added"),
                "slug": coin.get("slug"),
            },
        }

    def normalize_to_project(self, coin: dict) -> dict:
        """Normalize CMC coin data to project format."""
        platform = coin.get("platform") or {}
        return {
            "name": coin.get("name", ""),
            "symbol": coin.get("symbol"),
            "slug": f"cmc-{coin.get('slug', coin.get('id', ''))}",
            "contract_address": platform.get("token_address"),
            "blockchain": (platform.get("name") or "unknown").lower(),
            "source": "coinmarketcap",
            "extra_data": {
                "cmc_id": coin.get("id"),
                "cmc_rank": coin.get("cmc_rank"),
                "tags": coin.get("tags", []),
                "date_added": coin.get("date_added"),
            },
        }
