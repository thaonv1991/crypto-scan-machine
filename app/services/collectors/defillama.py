"""
DeFiLlama Collector - Free, open-source DeFi analytics.
No authentication required. Covers TVL, protocol data, token prices,
DEX volumes, and fee/revenue data.
"""

import structlog

from app.services.collectors.base import BaseCollector

logger = structlog.get_logger()

BASE_URL = "https://api.llama.fi"
COINS_URL = "https://coins.llama.fi"


class DeFiLlamaCollector(BaseCollector):
    """Collector for DeFiLlama DeFi protocol and market data."""

    source_name = "defillama"
    rate_limit_name = "defillama"

    async def collect(self, **kwargs) -> list[dict]:
        """Collect top protocols by TVL."""
        protocols = await self.get_protocols()
        return [self.normalize_protocol_to_project(p) for p in protocols[:100]]

    async def get_protocols(self) -> list[dict]:
        """Get all protocols with their TVL data."""
        try:
            url = f"{BASE_URL}/protocols"
            data = await self.fetch(url)
            if isinstance(data, list):
                return data
            return []
        except Exception as e:
            logger.error("defillama.protocols_failed", error=str(e))
            return []

    async def get_protocol_detail(self, slug: str) -> dict | None:
        """Get detailed protocol info including historical TVL."""
        try:
            url = f"{BASE_URL}/protocol/{slug}"
            return await self.fetch(url)
        except Exception as e:
            logger.error("defillama.protocol_detail_failed", slug=slug, error=str(e))
            return None

    async def get_protocol_tvl(self, slug: str) -> float | None:
        """Get current TVL for a protocol."""
        try:
            url = f"{BASE_URL}/tvl/{slug}"
            data = await self.fetch(url)
            if isinstance(data, (int, float)):
                return float(data)
            return None
        except Exception as e:
            logger.error("defillama.tvl_failed", slug=slug, error=str(e))
            return None

    async def get_chains(self) -> list[dict]:
        """Get current TVL for all chains."""
        try:
            url = f"{BASE_URL}/v2/chains"
            data = await self.fetch(url)
            if isinstance(data, list):
                return data
            return []
        except Exception as e:
            logger.error("defillama.chains_failed", error=str(e))
            return []

    async def get_token_prices(self, coins: list[str]) -> dict:
        """Get current prices for tokens. Format: 'chain:address' or 'coingecko:id'."""
        try:
            coins_str = ",".join(coins)
            url = f"{COINS_URL}/prices/current/{coins_str}"
            data = await self.fetch(url)
            return data.get("coins", {})
        except Exception as e:
            logger.error("defillama.prices_failed", error=str(e))
            return {}

    async def get_dex_volumes(self) -> list[dict]:
        """Get DEX volume overview across all chains."""
        try:
            url = f"{BASE_URL}/overview/dexs"
            data = await self.fetch(url)
            return data.get("protocols", [])
        except Exception as e:
            logger.error("defillama.dex_volumes_failed", error=str(e))
            return []

    async def get_dex_volume_by_chain(self, chain: str) -> list[dict]:
        """Get DEX volumes for a specific chain."""
        try:
            url = f"{BASE_URL}/overview/dexs/{chain}"
            data = await self.fetch(url)
            return data.get("protocols", [])
        except Exception as e:
            logger.error("defillama.dex_volume_chain_failed", error=str(e))
            return []

    async def get_fees_overview(self) -> list[dict]:
        """Get fees and revenue overview for all protocols."""
        try:
            url = f"{BASE_URL}/overview/fees"
            data = await self.fetch(url)
            return data.get("protocols", [])
        except Exception as e:
            logger.error("defillama.fees_failed", error=str(e))
            return []

    async def get_stablecoins(self) -> list[dict]:
        """Get stablecoin data across all chains."""
        try:
            url = "https://stablecoins.llama.fi/stablecoins"
            data = await self.fetch(url)
            return data.get("peggedAssets", [])
        except Exception as e:
            logger.error("defillama.stablecoins_failed", error=str(e))
            return []

    def normalize_protocol_to_project(self, protocol: dict) -> dict:
        """Normalize a DeFiLlama protocol to project format."""
        chains = protocol.get("chains", [])
        blockchain = chains[0].lower() if chains else "multi-chain"

        return {
            "name": protocol.get("name", ""),
            "symbol": protocol.get("symbol"),
            "slug": f"defillama-{protocol.get('slug', protocol.get('name', '').lower())}",
            "blockchain": blockchain,
            "website": protocol.get("url"),
            "description": protocol.get("description"),
            "logo_url": protocol.get("logo"),
            "twitter_url": f"https://twitter.com/{protocol['twitter']}" if protocol.get("twitter") else None,
            "source": "defillama",
            "extra_data": {
                "category": protocol.get("category"),
                "tvl": protocol.get("tvl"),
                "chain_tvls": protocol.get("chainTvls", {}),
                "change_1h": protocol.get("change_1h"),
                "change_1d": protocol.get("change_1d"),
                "change_7d": protocol.get("change_7d"),
                "mcap": protocol.get("mcap"),
                "fdv": protocol.get("fdv"),
                "chains": chains,
                "audit_links": protocol.get("audit_links", []),
                "gecko_id": protocol.get("gecko_id"),
                "cmc_id": protocol.get("cmcId"),
            },
        }

    def normalize_protocol_to_market_data(self, protocol: dict) -> dict:
        """Normalize protocol data to market data format."""
        return {
            "price_usd": None,
            "volume_24h": None,
            "market_cap": protocol.get("mcap"),
            "fdv": protocol.get("fdv"),
            "liquidity_usd": protocol.get("tvl"),
            "price_change_1h": protocol.get("change_1h"),
            "price_change_24h": protocol.get("change_1d"),
            "price_change_7d": protocol.get("change_7d"),
            "source": "defillama",
            "extra_data": {
                "category": protocol.get("category"),
                "tvl": protocol.get("tvl"),
                "chains": protocol.get("chains", []),
            },
        }
