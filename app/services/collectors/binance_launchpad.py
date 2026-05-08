"""
Binance Launchpad Collector - New token launches via Binance Launchpad/Launchpool.
No API key required - uses public Binance API.

Endpoints used:
- GET /bapi/lending/v1/friendly/launchpad/project/list - Launchpad projects
- GET /bapi/lending/v1/friendly/launchpool/project/list - Launchpool projects
"""

import structlog

from app.services.collectors.base import BaseCollector

logger = structlog.get_logger()

LAUNCHPAD_URL = "https://www.binance.com/bapi/lending/v1/friendly/launchpad/project/list"
LAUNCHPOOL_URL = "https://www.binance.com/bapi/lending/v1/friendly/launchpool/project/list"


class BinanceLaunchpadCollector(BaseCollector):
    """Collect token launch data from Binance Launchpad and Launchpool."""

    source_name = "binance_launchpad"
    rate_limit_name = "binance_launchpad"

    async def _fetch_post(self, url: str, payload: dict) -> dict:
        """Binance uses POST for some list endpoints."""
        from app.utils.rate_limiter import rate_limiters

        await rate_limiters.wait_and_acquire(self.rate_limit_name)
        client = await self.get_client()
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    async def get_launchpad_projects(self, page: int = 1, page_size: int = 20) -> list[dict]:
        """Get Binance Launchpad (IEO) projects."""
        try:
            data = await self._fetch_post(
                LAUNCHPAD_URL,
                {"pageNo": page, "pageSize": page_size},
            )
            return data.get("data", {}).get("list", []) if isinstance(data, dict) else []
        except Exception as e:
            logger.error("binance_launchpad.launchpad_failed", error=str(e))
            return []

    async def get_launchpool_projects(self, page: int = 1, page_size: int = 20) -> list[dict]:
        """Get Binance Launchpool (farming) projects."""
        try:
            data = await self._fetch_post(
                LAUNCHPOOL_URL,
                {"pageNo": page, "pageSize": page_size},
            )
            return data.get("data", {}).get("list", []) if isinstance(data, dict) else []
        except Exception as e:
            logger.error("binance_launchpad.launchpool_failed", error=str(e))
            return []

    async def collect(self, **kwargs) -> list[dict]:
        """Collect launch data from both Launchpad and Launchpool."""
        mode = kwargs.get("mode", "all")
        all_projects = []

        if mode in ("all", "launchpad"):
            projects = await self.get_launchpad_projects()
            for p in projects:
                all_projects.append(self.normalize_to_project(p, "launchpad"))

        if mode in ("all", "launchpool"):
            projects = await self.get_launchpool_projects()
            for p in projects:
                all_projects.append(self.normalize_to_project(p, "launchpool"))

        return all_projects

    def normalize_to_project(self, raw: dict, launch_type: str = "launchpad") -> dict:
        """Normalize Binance launch data to project format."""
        token_symbol = raw.get("asset") or raw.get("symbol") or ""
        project_name = raw.get("projectName") or raw.get("name") or token_symbol

        blockchain = "ethereum"
        network = (raw.get("network") or raw.get("chain") or "").lower()
        if "bsc" in network or "bnb" in network:
            blockchain = "bsc"
        elif "solana" in network:
            blockchain = "solana"

        return {
            "name": project_name,
            "symbol": token_symbol,
            "slug": f"binance-{launch_type}-{token_symbol}".lower(),
            "contract_address": raw.get("contractAddress"),
            "blockchain": blockchain,
            "website": raw.get("website") or raw.get("projectLink"),
            "description": raw.get("description"),
            "logo_url": raw.get("icon") or raw.get("logo"),
            "source": f"binance_{launch_type}",
            "extra_data": {
                "launch_type": launch_type,
                "status": raw.get("status"),
                "total_amount": raw.get("totalAmount"),
                "hard_cap": raw.get("hardCap"),
                "session_supply": raw.get("sessionSupply"),
                "start_time": raw.get("startTime"),
                "end_time": raw.get("endTime"),
                "listing_date": raw.get("listingDate"),
                "initial_circulating_supply": raw.get("initialCirculatingSupply"),
                "launchpad_price": raw.get("launchPrice") or raw.get("price"),
                "total_participants": raw.get("totalParticipants"),
                "total_committed": raw.get("totalCommitted"),
            },
        }
