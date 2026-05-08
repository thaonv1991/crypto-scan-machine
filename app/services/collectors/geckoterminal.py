"""
GeckoTerminal Collector - Free DEX data aggregator across 200+ chains.
No authentication required. Rate limit: ~10 calls/min (free tier).
"""

import structlog

from app.services.collectors.base import BaseCollector

logger = structlog.get_logger()

BASE_URL = "https://api.geckoterminal.com/api/v2"

NETWORK_MAP = {
    "ethereum": "eth",
    "bsc": "bsc",
    "polygon": "polygon_pos",
    "arbitrum": "arbitrum",
    "base": "base",
    "solana": "solana",
    "avalanche": "avax",
    "optimism": "optimism",
    "fantom": "ftm",
}


class GeckoTerminalCollector(BaseCollector):
    """Collector for GeckoTerminal DEX data across multiple chains."""

    source_name = "geckoterminal"
    rate_limit_name = "geckoterminal"

    async def collect(self, **kwargs) -> list[dict]:
        """Collect trending pools from GeckoTerminal."""
        pools = await self.get_trending_pools()
        return [self.normalize_pool_to_market_data(p) for p in pools if p]

    async def get_trending_pools(self, network: str | None = None) -> list[dict]:
        """Get trending pools across all networks or a specific one."""
        try:
            if network:
                net_id = NETWORK_MAP.get(network, network)
                url = f"{BASE_URL}/networks/{net_id}/trending_pools"
            else:
                url = f"{BASE_URL}/networks/trending_pools"
            data = await self.fetch(url)
            return data.get("data", [])
        except Exception as e:
            logger.error("geckoterminal.trending_pools_failed", error=str(e))
            return []

    async def get_top_pools(self, network: str = "eth") -> list[dict]:
        """Get top pools by volume for a network."""
        try:
            net_id = NETWORK_MAP.get(network, network)
            url = f"{BASE_URL}/networks/{net_id}/pools"
            data = await self.fetch(url)
            return data.get("data", [])
        except Exception as e:
            logger.error("geckoterminal.top_pools_failed", error=str(e))
            return []

    async def get_new_pools(self, network: str = "eth") -> list[dict]:
        """Get newly created pools for a network."""
        try:
            net_id = NETWORK_MAP.get(network, network)
            url = f"{BASE_URL}/networks/{net_id}/new_pools"
            data = await self.fetch(url)
            return data.get("data", [])
        except Exception as e:
            logger.error("geckoterminal.new_pools_failed", error=str(e))
            return []

    async def get_pool_details(self, network: str, pool_address: str) -> dict | None:
        """Get details for a specific pool."""
        try:
            net_id = NETWORK_MAP.get(network, network)
            url = f"{BASE_URL}/networks/{net_id}/pools/{pool_address}"
            data = await self.fetch(url)
            return data.get("data")
        except Exception as e:
            logger.error("geckoterminal.pool_details_failed", error=str(e))
            return None

    async def get_token_pools(self, network: str, token_address: str) -> list[dict]:
        """Get all pools for a specific token."""
        try:
            net_id = NETWORK_MAP.get(network, network)
            url = f"{BASE_URL}/networks/{net_id}/tokens/{token_address}/pools"
            data = await self.fetch(url)
            return data.get("data", [])
        except Exception as e:
            logger.error("geckoterminal.token_pools_failed", error=str(e))
            return []

    async def get_token_info(self, network: str, token_address: str) -> dict | None:
        """Get token info including price and volume."""
        try:
            net_id = NETWORK_MAP.get(network, network)
            url = f"{BASE_URL}/networks/{net_id}/tokens/{token_address}"
            data = await self.fetch(url)
            return data.get("data")
        except Exception as e:
            logger.error("geckoterminal.token_info_failed", error=str(e))
            return None

    async def search_pools(self, query: str) -> list[dict]:
        """Search for pools by token name, symbol, or address."""
        try:
            url = f"{BASE_URL}/search/pools"
            data = await self.fetch(url, params={"query": query})
            return data.get("data", [])
        except Exception as e:
            logger.error("geckoterminal.search_pools_failed", error=str(e))
            return []

    async def get_ohlcv(
        self,
        network: str,
        pool_address: str,
        timeframe: str = "day",
        aggregate: int = 1,
        limit: int = 30,
    ) -> list[dict]:
        """Get OHLCV candlestick data for a pool."""
        try:
            net_id = NETWORK_MAP.get(network, network)
            url = f"{BASE_URL}/networks/{net_id}/pools/{pool_address}/ohlcv/{timeframe}"
            data = await self.fetch(url, params={"aggregate": aggregate, "limit": limit})
            meta = data.get("data", {})
            return meta.get("attributes", {}).get("ohlcv_list", [])
        except Exception as e:
            logger.error("geckoterminal.ohlcv_failed", error=str(e))
            return []

    async def get_supported_networks(self) -> list[dict]:
        """Get list of supported networks."""
        try:
            url = f"{BASE_URL}/networks"
            data = await self.fetch(url)
            return data.get("data", [])
        except Exception as e:
            logger.error("geckoterminal.networks_failed", error=str(e))
            return []

    def normalize_pool_to_market_data(self, pool: dict) -> dict:
        """Normalize a pool object to market data format."""
        attrs = pool.get("attributes", {})
        relationships = pool.get("relationships", {})

        base_token = relationships.get("base_token", {}).get("data", {})
        quote_token = relationships.get("quote_token", {}).get("data", {})
        dex = relationships.get("dex", {}).get("data", {})

        price_changes = attrs.get("price_change_percentage", {})
        volume = attrs.get("volume_usd", {})
        txns = attrs.get("transactions", {})
        h24 = txns.get("h24", {})

        return {
            "name": attrs.get("name", ""),
            "pool_address": attrs.get("address", ""),
            "price_usd": float(attrs["base_token_price_usd"]) if attrs.get("base_token_price_usd") else None,
            "volume_24h": float(volume["h24"]) if volume.get("h24") else None,
            "market_cap": float(attrs["market_cap_usd"]) if attrs.get("market_cap_usd") else None,
            "fdv": float(attrs["fdv_usd"]) if attrs.get("fdv_usd") else None,
            "liquidity_usd": float(attrs["reserve_in_usd"]) if attrs.get("reserve_in_usd") else None,
            "price_change_5m": float(price_changes["m5"]) if price_changes.get("m5") else None,
            "price_change_1h": float(price_changes["h1"]) if price_changes.get("h1") else None,
            "price_change_24h": float(price_changes["h24"]) if price_changes.get("h24") else None,
            "buy_count": h24.get("buys"),
            "sell_count": h24.get("sells"),
            "source": "geckoterminal",
            "extra_data": {
                "base_token_id": base_token.get("id"),
                "quote_token_id": quote_token.get("id"),
                "dex_id": dex.get("id"),
                "pool_created_at": attrs.get("pool_created_at"),
            },
        }

    def normalize_pool_to_project(self, pool: dict) -> dict:
        """Normalize a pool to a project discovery format."""
        attrs = pool.get("attributes", {})
        relationships = pool.get("relationships", {})
        network = relationships.get("network", {}).get("data", {})
        network_id = network.get("id", "")

        blockchain_map = {v: k for k, v in NETWORK_MAP.items()}
        blockchain = blockchain_map.get(network_id, network_id)

        token_name = attrs.get("name", "").split(" / ")[0] if attrs.get("name") else ""

        return {
            "name": token_name,
            "slug": f"gt-{network_id}-{attrs.get('address', '')}",
            "blockchain": blockchain,
            "contract_address": attrs.get("address"),
            "source": "geckoterminal",
            "extra_data": {
                "pool_address": attrs.get("address"),
                "pool_created_at": attrs.get("pool_created_at"),
                "fdv_usd": attrs.get("fdv_usd"),
                "reserve_in_usd": attrs.get("reserve_in_usd"),
            },
        }
