"""
LunarCrush Collector - Social intelligence and sentiment data.
*** REQUIRES API KEY ***
Get API key at: https://lunarcrush.com/developers/api

Provides Galaxy Score, AltRank, social volume, sentiment, and influencer data.
"""

import structlog

from app.core.config import settings
from app.services.collectors.base import BaseCollector

logger = structlog.get_logger()

BASE_URL = "https://lunarcrush.com/api4/public"


class LunarCrushCollector(BaseCollector):
    """Collect social intelligence data from LunarCrush."""

    source_name = "lunarcrush"
    rate_limit_name = "lunarcrush"

    def _get_api_key(self) -> str:
        return settings.lunarcrush_api_key

    def is_configured(self) -> bool:
        return bool(settings.lunarcrush_api_key)

    async def fetch(self, url: str, params: dict | None = None) -> dict:
        if not self.is_configured():
            logger.warning("lunarcrush.not_configured", hint="Set LUNARCRUSH_API_KEY")
            return {}
        from app.utils.rate_limiter import rate_limiters

        await rate_limiters.wait_and_acquire(self.rate_limit_name)
        client = await self.get_client()
        headers = {"Authorization": f"Bearer {self._get_api_key()}"}
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()

    async def get_coin_data(self, symbol: str) -> dict | None:
        """Get comprehensive social + market data for a coin."""
        try:
            url = f"{BASE_URL}/coins/{symbol}/v1"
            data = await self.fetch(url)
            return data.get("data") if data else None
        except Exception as e:
            logger.error("lunarcrush.coin_data_failed", symbol=symbol, error=str(e))
            return None

    async def get_coin_time_series(self, symbol: str, interval: str = "1d", limit: int = 30) -> list[dict]:
        """Get time-series social data for a coin.

        Args:
            interval: '1h', '1d', '1w'
        """
        try:
            url = f"{BASE_URL}/coins/{symbol}/time-series/v2"
            data = await self.fetch(url, params={"interval": interval, "limit": limit})
            return data.get("data", []) if data else []
        except Exception as e:
            logger.error("lunarcrush.time_series_failed", symbol=symbol, error=str(e))
            return []

    async def get_trending_coins(self, limit: int = 50) -> list[dict]:
        """Get trending coins by social activity."""
        try:
            url = f"{BASE_URL}/coins/list/v2"
            data = await self.fetch(url, params={"sort": "galaxy_score", "limit": limit})
            return data.get("data", []) if data else []
        except Exception as e:
            logger.error("lunarcrush.trending_failed", error=str(e))
            return []

    async def get_coin_feeds(self, symbol: str, limit: int = 20) -> list[dict]:
        """Get social media posts/feeds mentioning a coin."""
        try:
            url = f"{BASE_URL}/coins/{symbol}/feeds/v1"
            data = await self.fetch(url, params={"limit": limit})
            return data.get("data", []) if data else []
        except Exception as e:
            logger.error("lunarcrush.feeds_failed", symbol=symbol, error=str(e))
            return []

    async def collect(self, **kwargs) -> list[dict]:
        """Collect social intelligence from LunarCrush."""
        if not self.is_configured():
            logger.warning("lunarcrush.skipped", reason="API key not configured")
            return []

        symbol = kwargs.get("symbol", "")
        if not symbol:
            mode = kwargs.get("mode", "trending")
            if mode == "trending":
                return await self.get_trending_coins()
            return []

        coin = await self.get_coin_data(symbol)
        return [self.normalize_to_social_data(coin)] if coin else []

    def normalize_to_social_data(self, raw: dict) -> dict:
        """Normalize LunarCrush data to social data format."""
        return {
            "platform": "lunarcrush",
            "galaxy_score": raw.get("galaxy_score"),
            "alt_rank": raw.get("alt_rank"),
            "social_volume": raw.get("social_volume"),
            "social_score": raw.get("social_score"),
            "social_contributors": raw.get("social_contributors"),
            "social_dominance": raw.get("social_dominance"),
            "sentiment": raw.get("sentiment"),
            "market_dominance": raw.get("market_dominance"),
            "source": "lunarcrush",
            "extra_data": {
                "symbol": raw.get("symbol"),
                "name": raw.get("name"),
                "price": raw.get("price"),
                "market_cap": raw.get("market_cap"),
                "volume_24h": raw.get("volume_24h"),
                "percent_change_24h": raw.get("percent_change_24h"),
                "twitter_volume": raw.get("tweet_volume"),
                "reddit_volume": raw.get("reddit_posts"),
                "news_volume": raw.get("news"),
                "url_shares": raw.get("url_shares"),
                "categories": raw.get("categories"),
            },
        }

    def normalize_to_project_score(self, raw: dict) -> dict:
        """Extract scoring-relevant data from LunarCrush."""
        return {
            "galaxy_score": raw.get("galaxy_score"),
            "alt_rank": raw.get("alt_rank"),
            "social_score": raw.get("social_score"),
            "sentiment": raw.get("sentiment"),
            "social_volume": raw.get("social_volume"),
            "social_contributors": raw.get("social_contributors"),
        }
