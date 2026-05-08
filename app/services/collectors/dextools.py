"""
DEXTools Collector - Token and pair analytics across multiple chains.
Requires API key for all endpoints.
Get API key at: https://developer.dextools.io (apply via form)
"""

import os

import structlog

from app.services.collectors.base import BaseCollector

logger = structlog.get_logger()

BASE_URL = "https://public-api.dextools.io/standard/v2"

CHAIN_MAP = {
    "ethereum": "ether",
    "bsc": "bsc",
    "polygon": "polygon",
    "arbitrum": "arbitrum",
    "base": "base",
    "solana": "solana",
    "avalanche": "avalanche",
    "optimism": "optimism",
    "fantom": "fantom",
}


class DEXToolsCollector(BaseCollector):
    """Collector for DEXTools token/pair analytics. Requires DEXTOOLS_API_KEY."""

    source_name = "dextools"
    rate_limit_name = "dextools"

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("DEXTOOLS_API_KEY", "")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def fetch(self, url: str, params: dict | None = None) -> dict:
        if not self.is_configured():
            logger.warning("dextools.not_configured")
            return {}
        from app.utils.rate_limiter import rate_limiters

        await rate_limiters.wait_and_acquire(self.rate_limit_name)
        client = await self.get_client()
        response = await client.get(
            url,
            params=params,
            headers={"X-BLOBR-KEY": self.api_key, "Accept": "application/json"},
        )
        response.raise_for_status()
        return response.json()

    async def collect(self, **kwargs) -> list[dict]:
        if not self.is_configured():
            return []
        chain = kwargs.get("chain", "ether")
        hot_pools = await self.get_hot_pools(chain)
        return [self.normalize_pool_to_market_data(p) for p in hot_pools]

    async def get_token_info(self, chain: str, token_address: str) -> dict | None:
        """Get token details including audit info."""
        try:
            chain_slug = CHAIN_MAP.get(chain, chain)
            url = f"{BASE_URL}/token/{chain_slug}/{token_address}"
            data = await self.fetch(url)
            return data.get("data")
        except Exception as e:
            logger.error("dextools.token_info_failed", error=str(e))
            return None

    async def get_token_pools(self, chain: str, token_address: str) -> list[dict]:
        """Get pools for a token."""
        try:
            chain_slug = CHAIN_MAP.get(chain, chain)
            url = f"{BASE_URL}/token/{chain_slug}/{token_address}/pools"
            data = await self.fetch(url)
            return data.get("data", {}).get("results", [])
        except Exception as e:
            logger.error("dextools.token_pools_failed", error=str(e))
            return []

    async def get_token_score(self, chain: str, token_address: str) -> dict | None:
        """Get DEXTools score for a token (audit, community, info scores)."""
        try:
            chain_slug = CHAIN_MAP.get(chain, chain)
            url = f"{BASE_URL}/token/{chain_slug}/{token_address}/score"
            data = await self.fetch(url)
            return data.get("data")
        except Exception as e:
            logger.error("dextools.token_score_failed", error=str(e))
            return None

    async def get_hot_pools(self, chain: str = "ether") -> list[dict]:
        """Get hot/trending pools for a chain."""
        try:
            chain_slug = CHAIN_MAP.get(chain, chain)
            url = f"{BASE_URL}/ranking/{chain_slug}/hotpools"
            data = await self.fetch(url)
            return data.get("data", [])
        except Exception as e:
            logger.error("dextools.hot_pools_failed", error=str(e))
            return []

    async def get_gainers(self, chain: str = "ether") -> list[dict]:
        """Get top gaining tokens."""
        try:
            chain_slug = CHAIN_MAP.get(chain, chain)
            url = f"{BASE_URL}/ranking/{chain_slug}/gainers"
            data = await self.fetch(url)
            return data.get("data", [])
        except Exception as e:
            logger.error("dextools.gainers_failed", error=str(e))
            return []

    async def get_losers(self, chain: str = "ether") -> list[dict]:
        """Get top losing tokens."""
        try:
            chain_slug = CHAIN_MAP.get(chain, chain)
            url = f"{BASE_URL}/ranking/{chain_slug}/losers"
            data = await self.fetch(url)
            return data.get("data", [])
        except Exception as e:
            logger.error("dextools.losers_failed", error=str(e))
            return []

    def normalize_pool_to_market_data(self, pool: dict) -> dict:
        """Normalize DEXTools pool data to market data format."""
        main_token = pool.get("mainToken", {})
        return {
            "name": main_token.get("name", ""),
            "symbol": main_token.get("symbol", ""),
            "contract_address": main_token.get("address"),
            "price_usd": pool.get("price"),
            "volume_24h": pool.get("volume24h"),
            "market_cap": main_token.get("mcap"),
            "liquidity_usd": pool.get("liquidity"),
            "price_change_24h": pool.get("priceChange24h"),
            "source": "dextools",
            "extra_data": {
                "pair_address": pool.get("address"),
                "exchange_name": pool.get("exchange", {}).get("name"),
                "creation_time": pool.get("creationTime"),
                "dext_score": pool.get("dextScore"),
            },
        }

    def normalize_to_project(self, token: dict) -> dict:
        """Normalize DEXTools token data to project format."""
        info = token.get("info", {})
        links = token.get("links", {})
        return {
            "name": info.get("name", ""),
            "symbol": info.get("symbol"),
            "slug": f"dextools-{info.get('address', '')}",
            "contract_address": info.get("address"),
            "blockchain": token.get("chain", "ethereum"),
            "website": links.get("website"),
            "twitter_url": links.get("twitter"),
            "telegram_url": links.get("telegram"),
            "logo_url": info.get("logo"),
            "description": info.get("description"),
            "source": "dextools",
            "extra_data": {
                "dext_score": token.get("dextScore"),
                "audit": token.get("audit"),
                "creation_time": info.get("creationTime"),
                "total_supply": info.get("totalSupply"),
            },
        }
