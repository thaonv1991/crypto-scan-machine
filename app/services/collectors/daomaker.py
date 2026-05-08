"""
DAO Maker Collector - Token launches and SHO (Strong Holder Offering).
No API key required - uses public API.

DAO Maker is a top-tier launchpad for vetted crypto projects.

Endpoints used:
- GET /api/v1/offers - List SHO offers
- GET /api/v1/offers/{id} - Offer details
"""

import structlog

from app.services.collectors.base import BaseCollector

logger = structlog.get_logger()

BASE_URL = "https://api.daomaker.com"


class DAOMakerCollector(BaseCollector):
    """Collect upcoming SHO and launch data from DAO Maker."""

    source_name = "daomaker"
    rate_limit_name = "daomaker"

    async def get_offers(self, status: str = "open", page: int = 1, limit: int = 20) -> list[dict]:
        """Get list of SHO offers.

        Args:
            status: 'open', 'upcoming', 'closed', 'all'
        """
        url = f"{BASE_URL}/api/v1/offers"
        try:
            data = await self.fetch(
                url,
                params={"status": status, "page": page, "limit": limit},
            )
            if isinstance(data, dict):
                return data.get("data", [])
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error("daomaker.offers_failed", status=status, error=str(e))
            return []

    async def get_offer_details(self, offer_id: str) -> dict | None:
        """Get detailed info for a specific SHO offer."""
        url = f"{BASE_URL}/api/v1/offers/{offer_id}"
        try:
            data = await self.fetch(url)
            return data.get("data") if isinstance(data, dict) else data
        except Exception as e:
            logger.error("daomaker.offer_details_failed", offer_id=offer_id, error=str(e))
            return None

    async def get_completed_projects(self, page: int = 1, limit: int = 50) -> list[dict]:
        """Get list of completed/launched projects for historical analysis."""
        return await self.get_offers(status="closed", page=page, limit=limit)

    async def collect(self, **kwargs) -> list[dict]:
        """Collect launch data from DAO Maker."""
        status = kwargs.get("status", "open")
        include_upcoming = kwargs.get("include_upcoming", True)

        all_projects = []

        offers = await self.get_offers(status=status)
        for offer in offers:
            all_projects.append(self.normalize_to_project(offer))

        if include_upcoming and status != "upcoming":
            upcoming = await self.get_offers(status="upcoming")
            for offer in upcoming:
                all_projects.append(self.normalize_to_project(offer))

        return all_projects

    def normalize_to_project(self, raw: dict) -> dict:
        """Normalize DAO Maker offer to project format."""
        social = raw.get("social", {}) or {}
        token_info = raw.get("token", {}) or {}

        blockchain = "ethereum"
        network = (raw.get("network") or raw.get("chain") or "").lower()
        if "bsc" in network or "bnb" in network:
            blockchain = "bsc"
        elif "solana" in network or "sol" in network:
            blockchain = "solana"
        elif "polygon" in network:
            blockchain = "polygon"
        elif "arbitrum" in network:
            blockchain = "arbitrum"
        elif "base" in network:
            blockchain = "base"

        return {
            "name": raw.get("name", ""),
            "symbol": token_info.get("symbol") or raw.get("symbol"),
            "slug": f"daomaker-{raw.get('id', '')}",
            "contract_address": token_info.get("address"),
            "blockchain": blockchain,
            "website": social.get("website") or raw.get("website"),
            "description": raw.get("shortDescription") or raw.get("description"),
            "logo_url": raw.get("logo") or raw.get("image"),
            "twitter_url": social.get("twitter"),
            "telegram_url": social.get("telegram"),
            "discord_url": social.get("discord"),
            "source": "daomaker",
            "extra_data": {
                "offer_id": raw.get("id"),
                "offer_type": raw.get("type"),
                "status": raw.get("status"),
                "raise_amount": raw.get("raiseAmount"),
                "token_price": raw.get("tokenPrice") or token_info.get("price"),
                "total_supply": token_info.get("totalSupply"),
                "market_cap_at_launch": raw.get("marketCap"),
                "vesting": raw.get("vesting"),
                "start_date": raw.get("startDate"),
                "end_date": raw.get("endDate"),
                "participants": raw.get("participants"),
                "tier": raw.get("tier"),
                "category": raw.get("category"),
            },
        }
