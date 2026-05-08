"""
DexScreener Collector - Engine 1 & 2 (partial)
Free API, no authentication required.
Rate limit: 60 req/min (token profiles), 300 req/min (dex pairs)

Endpoints used:
- GET /token-profiles/latest/v1 - Latest token profiles
- GET /latest/dex/search?q=QUERY - Search tokens/pairs
- GET /latest/dex/pairs/{chainId}/{pairAddress} - Pair details
- GET /latest/dex/tokens/{tokenAddress} - Token info across chains
- GET /token-boosts/top/v1 - Top boosted tokens (trending)
"""

import structlog

from app.services.collectors.base import BaseCollector

logger = structlog.get_logger()

BASE_URL = "https://api.dexscreener.com"

CHAIN_MAP = {
    "ethereum": "ethereum",
    "bsc": "bsc",
    "solana": "solana",
    "base": "base",
    "arbitrum": "arbitrum",
    "polygon": "polygon",
    "avalanche": "avalanche",
}


class DexScreenerCollector(BaseCollector):
    """Collect new token listings and market data from DexScreener."""

    source_name = "dexscreener"
    rate_limit_name = "dexscreener"

    async def get_latest_token_profiles(self) -> list[dict]:
        """Get the latest token profiles (new listings)."""
        url = f"{BASE_URL}/token-profiles/latest/v1"
        try:
            data = await self.fetch(url)
            if isinstance(data, list):
                return data
            return []
        except Exception as e:
            logger.error("dexscreener.token_profiles_failed", error=str(e))
            return []

    async def get_top_boosted_tokens(self) -> list[dict]:
        """Get top boosted tokens (trending/promoted)."""
        url = f"{BASE_URL}/token-boosts/top/v1"
        try:
            data = await self.fetch(url)
            if isinstance(data, list):
                return data
            return []
        except Exception as e:
            logger.error("dexscreener.boosted_tokens_failed", error=str(e))
            return []

    async def search_tokens(self, query: str) -> list[dict]:
        """Search for tokens/pairs by name, symbol or address."""
        url = f"{BASE_URL}/latest/dex/search"
        try:
            data = await self.fetch(url, params={"q": query})
            return data.get("pairs", [])
        except Exception as e:
            logger.error("dexscreener.search_failed", query=query, error=str(e))
            return []

    async def get_pair_details(self, chain_id: str, pair_address: str) -> dict | None:
        """Get detailed info for a specific pair."""
        url = f"{BASE_URL}/latest/dex/pairs/{chain_id}/{pair_address}"
        try:
            data = await self.fetch(url)
            pairs = data.get("pairs", [])
            return pairs[0] if pairs else None
        except Exception as e:
            logger.error(
                "dexscreener.pair_details_failed",
                chain_id=chain_id,
                pair_address=pair_address,
                error=str(e),
            )
            return None

    async def get_token_info(self, token_address: str) -> list[dict]:
        """Get token info across all chains."""
        url = f"{BASE_URL}/latest/dex/tokens/{token_address}"
        try:
            data = await self.fetch(url)
            return data.get("pairs", [])
        except Exception as e:
            logger.error("dexscreener.token_info_failed", token_address=token_address, error=str(e))
            return []

    async def collect(self, **kwargs) -> list[dict]:
        """Collect new token listings from DexScreener."""
        mode = kwargs.get("mode", "latest")

        if mode == "latest":
            return await self.get_latest_token_profiles()
        elif mode == "boosted":
            return await self.get_top_boosted_tokens()
        elif mode == "search":
            query = kwargs.get("query", "")
            return await self.search_tokens(query)
        else:
            return await self.get_latest_token_profiles()

    def normalize_token_profile(self, raw: dict) -> dict:
        """Normalize a DexScreener token profile to our project format."""
        links = raw.get("links") or []
        twitter_url = None
        telegram_url = None
        discord_url = None
        website = None

        for link in links:
            link_type = (link.get("type") or "").lower()
            link_label = (link.get("label") or "").lower()
            link_url = link.get("url", "")

            if link_type == "twitter" or "twitter" in link_label or "x.com" in link_url:
                twitter_url = link_url
            elif link_type == "telegram" or "telegram" in link_label:
                telegram_url = link_url
            elif link_type == "discord" or "discord" in link_label:
                discord_url = link_url
            elif link_type == "website" or link_label == "website":
                website = link_url

        chain_id = raw.get("chainId", "unknown")
        token_address = raw.get("tokenAddress", "")

        return {
            "name": raw.get("description", token_address[:20]) or token_address[:20],
            "symbol": None,
            "slug": f"dexscreener-{chain_id}-{token_address}".lower(),
            "contract_address": token_address,
            "blockchain": CHAIN_MAP.get(chain_id, chain_id),
            "website": website,
            "description": raw.get("description"),
            "logo_url": raw.get("icon"),
            "twitter_url": twitter_url,
            "telegram_url": telegram_url,
            "discord_url": discord_url,
            "source": "dexscreener",
            "extra_data": {
                "chain_id": chain_id,
                "dexscreener_url": raw.get("url"),
                "header_image": raw.get("header"),
            },
        }

    def normalize_pair_to_market_data(self, pair: dict) -> dict:
        """Normalize a DexScreener pair to our market data format."""
        price_change = pair.get("priceChange", {})

        return {
            "price_usd": _safe_float(pair.get("priceUsd")),
            "volume_24h": _safe_float(pair.get("volume", {}).get("h24")),
            "market_cap": _safe_float(pair.get("marketCap")),
            "fdv": _safe_float(pair.get("fdv")),
            "liquidity_usd": _safe_float(pair.get("liquidity", {}).get("usd")),
            "price_change_1h": _safe_float(price_change.get("h1")),
            "price_change_24h": _safe_float(price_change.get("h24")),
            "buy_count": pair.get("txns", {}).get("h24", {}).get("buys"),
            "sell_count": pair.get("txns", {}).get("h24", {}).get("sells"),
            "source": "dexscreener",
            "extra_data": {
                "pair_address": pair.get("pairAddress"),
                "dex_id": pair.get("dexId"),
                "chain_id": pair.get("chainId"),
                "base_token": pair.get("baseToken"),
                "quote_token": pair.get("quoteToken"),
                "price_native": pair.get("priceNative"),
            },
        }


def _safe_float(value: str | float | None) -> float | None:
    """Safely convert a value to float."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
