"""
CoinGecko Collector - Engine 2 (Market Data)
Free tier: ~30 req/min, no API key required for basic endpoints.
Optional API key for higher limits (x-cg-demo-api-key header).

Endpoints used:
- GET /api/v3/coins/markets - Coins list with market data
- GET /api/v3/coins/{id} - Coin details
- GET /api/v3/search/trending - Trending coins
- GET /api/v3/simple/price - Simple price lookup
- GET /api/v3/coins/{id}/market_chart - Historical market data
"""

from typing import Any

import structlog

from app.core.config import settings
from app.services.collectors.base import BaseCollector

logger = structlog.get_logger()

BASE_URL = "https://api.coingecko.com/api/v3"

PLATFORM_TO_BLOCKCHAIN = {
    "ethereum": "ethereum",
    "binance-smart-chain": "bsc",
    "solana": "solana",
    "base": "base",
    "arbitrum-one": "arbitrum",
    "polygon-pos": "polygon",
    "avalanche": "avalanche",
}


class CoinGeckoCollector(BaseCollector):
    """Collect market data from CoinGecko free API."""

    source_name = "coingecko"
    rate_limit_name = "coingecko"

    def _get_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if settings.coingecko_api_key:
            headers["x-cg-demo-api-key"] = settings.coingecko_api_key
        return headers

    async def fetch(self, url: str, params: dict | None = None) -> dict[str, Any]:  # type: ignore[override]
        """Override fetch to add CoinGecko API key header if available."""
        from app.utils.rate_limiter import rate_limiters

        await rate_limiters.wait_and_acquire(self.rate_limit_name)
        client = await self.get_client()
        response = await client.get(url, params=params, headers=self._get_headers())
        response.raise_for_status()
        data: Any = response.json()
        if isinstance(data, dict):
            return data
        return {"_list": data}

    async def get_trending_coins(self) -> list[dict]:
        """Get trending search coins on CoinGecko."""
        url = f"{BASE_URL}/search/trending"
        try:
            data = await self.fetch(url)
            coins: list[dict[str, Any]] = data.get("coins", [])
            return [c.get("item", {}) for c in coins]
        except Exception as e:
            logger.error("coingecko.trending_failed", error=str(e))
            return []

    async def get_coins_markets(
        self,
        vs_currency: str = "usd",
        per_page: int = 100,
        page: int = 1,
        order: str = "market_cap_desc",
        category: str | None = None,
    ) -> list[dict]:
        """Get coins list with market data."""
        url = f"{BASE_URL}/coins/markets"
        params: dict[str, str | int] = {
            "vs_currency": vs_currency,
            "per_page": per_page,
            "page": page,
            "order": order,
            "sparkline": "false",
            "price_change_percentage": "1h,24h,7d",
        }
        if category:
            params["category"] = category
        try:
            data = await self.fetch(url, params=params)
            raw_list: list[dict[str, Any]] = data.get("_list", []) if "_list" in data else [data]
            return raw_list if raw_list != [data] else []
        except ValueError:
            return []
        except Exception as e:
            logger.error("coingecko.markets_failed", error=str(e))
            return []

    async def get_coin_details(self, coin_id: str) -> dict | None:
        """Get detailed info for a specific coin."""
        url = f"{BASE_URL}/coins/{coin_id}"
        params = {
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "true",
            "developer_data": "false",
            "sparkline": "false",
        }
        try:
            result = await self.fetch(url, params=params)
            return result
        except Exception as e:
            logger.error("coingecko.coin_details_failed", coin_id=coin_id, error=str(e))
            return None

    async def get_simple_price(self, coin_ids: list[str], vs_currencies: str = "usd,btc,eth") -> dict:
        """Get simple price for multiple coins."""
        url = f"{BASE_URL}/simple/price"
        params = {
            "ids": ",".join(coin_ids),
            "vs_currencies": vs_currencies,
            "include_market_cap": "true",
            "include_24hr_vol": "true",
            "include_24hr_change": "true",
            "include_last_updated_at": "true",
        }
        try:
            result = await self.fetch(url, params=params)
            return result
        except Exception as e:
            logger.error("coingecko.simple_price_failed", error=str(e))
            return {}

    async def collect(self, **kwargs) -> list[dict]:
        """Collect market data from CoinGecko."""
        mode = kwargs.get("mode", "markets")

        if mode == "trending":
            return await self.get_trending_coins()
        elif mode == "markets":
            page = kwargs.get("page", 1)
            per_page = kwargs.get("per_page", 100)
            return await self.get_coins_markets(per_page=per_page, page=page)
        elif mode == "details":
            coin_id = kwargs.get("coin_id", "")
            result = await self.get_coin_details(coin_id)
            return [result] if result else []
        else:
            return await self.get_coins_markets()

    def normalize_market_data(self, coin: dict) -> dict:
        """Normalize CoinGecko market data to our MarketData format."""
        return {
            "price_usd": coin.get("current_price"),
            "price_btc": None,
            "price_eth": None,
            "volume_24h": coin.get("total_volume"),
            "market_cap": coin.get("market_cap"),
            "fdv": coin.get("fully_diluted_valuation"),
            "price_change_1h": coin.get("price_change_percentage_1h_in_currency"),
            "price_change_24h": coin.get("price_change_percentage_24h"),
            "price_change_7d": coin.get("price_change_percentage_7d_in_currency"),
            "holders_count": None,
            "source": "coingecko",
            "extra_data": {
                "coingecko_id": coin.get("id"),
                "market_cap_rank": coin.get("market_cap_rank"),
                "circulating_supply": coin.get("circulating_supply"),
                "total_supply": coin.get("total_supply"),
                "max_supply": coin.get("max_supply"),
                "ath": coin.get("ath"),
                "ath_date": coin.get("ath_date"),
                "atl": coin.get("atl"),
                "atl_date": coin.get("atl_date"),
            },
        }

    def normalize_to_project(self, coin: dict) -> dict:
        """Normalize CoinGecko coin data to our Project format."""
        return {
            "name": coin.get("name", ""),
            "symbol": coin.get("symbol", "").upper(),
            "slug": f"coingecko-{coin.get('id', '')}",
            "contract_address": None,
            "blockchain": "ethereum",
            "website": None,
            "description": None,
            "logo_url": coin.get("image") or coin.get("large") or coin.get("thumb"),
            "category": None,
            "twitter_url": None,
            "telegram_url": None,
            "discord_url": None,
            "source": "coingecko",
            "extra_data": {
                "coingecko_id": coin.get("id"),
                "market_cap_rank": coin.get("market_cap_rank"),
            },
        }

    def normalize_detail_to_project(self, detail: dict) -> dict:
        """Normalize detailed CoinGecko coin data to our Project format."""
        links = detail.get("links", {})
        homepage = links.get("homepage", [])
        twitter = links.get("twitter_screen_name", "")
        telegram = links.get("telegram_channel_identifier", "")
        subreddit = links.get("subreddit_url", "")
        repos = links.get("repos_url", {})
        github_urls = repos.get("github", [])

        platforms = detail.get("platforms", {})
        contract_address = None
        blockchain = "ethereum"
        for platform_name, addr in platforms.items():
            if addr:
                contract_address = addr
                blockchain = PLATFORM_TO_BLOCKCHAIN.get(platform_name, platform_name)
                break

        description_data = detail.get("description", {})
        description = description_data.get("en", "") if isinstance(description_data, dict) else ""

        return {
            "name": detail.get("name", ""),
            "symbol": (detail.get("symbol") or "").upper(),
            "slug": f"coingecko-{detail.get('id', '')}",
            "contract_address": contract_address,
            "blockchain": blockchain,
            "website": homepage[0] if homepage else None,
            "description": description[:500] if description else None,
            "logo_url": detail.get("image", {}).get("large"),
            "category": None,
            "twitter_url": f"https://twitter.com/{twitter}" if twitter else None,
            "telegram_url": f"https://t.me/{telegram}" if telegram else None,
            "discord_url": None,
            "github_url": github_urls[0] if github_urls else None,
            "source": "coingecko",
            "extra_data": {
                "coingecko_id": detail.get("id"),
                "market_cap_rank": detail.get("market_cap_rank"),
                "community_data": detail.get("community_data"),
                "categories": detail.get("categories"),
                "subreddit_url": subreddit,
            },
        }
