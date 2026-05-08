"""
Pinksale Collector - Upcoming token launches and presales.
No API key required - uses public API.

Pinksale is one of the largest crypto launchpads supporting
BSC, Ethereum, Polygon, Avalanche, Arbitrum, and more.

Endpoints used:
- GET /api/v1/pool/list - List presales/launches
- GET /api/v1/pool/{address} - Pool details
"""

import structlog

from app.services.collectors.base import BaseCollector

logger = structlog.get_logger()

BASE_URL = "https://api.pinksale.finance"

CHAIN_IDS = {
    "bsc": 56,
    "ethereum": 1,
    "polygon": 137,
    "avalanche": 43114,
    "arbitrum": 42161,
    "base": 8453,
}


class PinksaleCollector(BaseCollector):
    """Collect upcoming token launches from Pinksale launchpad."""

    source_name = "pinksale"
    rate_limit_name = "pinksale"

    async def get_presale_list(
        self,
        chain_id: int = 56,
        page: int = 1,
        page_size: int = 50,
        status: str = "upcoming",
    ) -> list[dict]:
        """Get list of presales/launches.

        Args:
            chain_id: Blockchain chain ID (56=BSC, 1=ETH, 137=Polygon, etc.)
            status: 'upcoming', 'inprogress', 'filled', 'ended'
        """
        url = f"{BASE_URL}/api/v1/pool/list"
        try:
            data = await self.fetch(
                url,
                params={
                    "chainId": chain_id,
                    "page": page,
                    "pageSize": page_size,
                    "status": status,
                },
            )
            return data.get("data", {}).get("docs", []) if isinstance(data, dict) else []
        except Exception as e:
            logger.error("pinksale.list_failed", chain_id=chain_id, status=status, error=str(e))
            return []

    async def get_pool_details(self, pool_address: str, chain_id: int = 56) -> dict | None:
        """Get detailed info for a specific presale pool."""
        url = f"{BASE_URL}/api/v1/pool/{pool_address}"
        try:
            data = await self.fetch(url, params={"chainId": chain_id})
            return data.get("data") if isinstance(data, dict) else None
        except Exception as e:
            logger.error("pinksale.details_failed", address=pool_address, error=str(e))
            return None

    async def collect(self, **kwargs) -> list[dict]:
        """Collect upcoming launches from Pinksale across multiple chains."""
        status = kwargs.get("status", "upcoming")
        chains = kwargs.get("chains", ["bsc", "ethereum", "base"])

        all_projects = []
        for chain_name in chains:
            chain_id = CHAIN_IDS.get(chain_name, 56)
            pools = await self.get_presale_list(chain_id=chain_id, status=status)
            for pool in pools:
                normalized = self.normalize_to_project(pool, chain_name)
                all_projects.append(normalized)

        return all_projects

    def normalize_to_project(self, raw: dict, blockchain: str = "bsc") -> dict:
        """Normalize Pinksale pool data to project format."""
        token = raw.get("token", {})
        social = raw.get("social", {})

        return {
            "name": token.get("name", ""),
            "symbol": token.get("symbol"),
            "slug": f"pinksale-{raw.get('poolAddress', '')}".lower(),
            "contract_address": token.get("address"),
            "blockchain": blockchain,
            "website": social.get("website"),
            "description": raw.get("description"),
            "logo_url": raw.get("logo") or raw.get("bannerUrl"),
            "twitter_url": social.get("twitter"),
            "telegram_url": social.get("telegram"),
            "discord_url": social.get("discord"),
            "github_url": social.get("github"),
            "source": "pinksale",
            "launch_date": raw.get("startTime"),
            "extra_data": {
                "pool_address": raw.get("poolAddress"),
                "pool_type": raw.get("poolType"),
                "status": raw.get("status"),
                "soft_cap": raw.get("softCap"),
                "hard_cap": raw.get("hardCap"),
                "rate": raw.get("rate"),
                "min_buy": raw.get("minBuy"),
                "max_buy": raw.get("maxBuy"),
                "total_raised": raw.get("totalRaised"),
                "participants": raw.get("participants"),
                "start_time": raw.get("startTime"),
                "end_time": raw.get("endTime"),
                "listing_time": raw.get("listingTime"),
                "liquidity_percent": raw.get("liquidityPercent"),
                "lockup_time": raw.get("lockupTime"),
                "kyc": raw.get("kyc"),
                "audit": raw.get("audit"),
            },
        }
