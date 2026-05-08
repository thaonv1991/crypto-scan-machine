"""
Solscan Collector - On-chain data for Solana.
*** REQUIRES API KEY ***
Free tier: 100 requests/day
Get API key at: https://pro.solscan.io/

Endpoints used:
- GET /v2.0/token/meta - Token metadata
- GET /v2.0/token/transfer - Token transfers
- GET /v2.0/token/holders - Token holders
- GET /v2.0/token/markets - Token market data
"""

import structlog

from app.core.config import settings
from app.services.collectors.base import BaseCollector

logger = structlog.get_logger()

BASE_URL = "https://pro-api.solscan.io/v2.0"


class SolscanCollector(BaseCollector):
    """Collect on-chain data from Solscan for Solana tokens."""

    source_name = "solscan"
    rate_limit_name = "solscan"

    def _get_headers(self) -> dict:
        return {"token": settings.solscan_api_key, "Accept": "application/json"}

    def is_configured(self) -> bool:
        return bool(settings.solscan_api_key)

    async def fetch(self, url: str, params: dict | None = None) -> dict:
        if not self.is_configured():
            logger.warning("solscan.not_configured", hint="Set SOLSCAN_API_KEY")
            return {}
        from app.utils.rate_limiter import rate_limiters

        await rate_limiters.wait_and_acquire(self.rate_limit_name)
        client = await self.get_client()
        response = await client.get(url, params=params, headers=self._get_headers())
        response.raise_for_status()
        return response.json()

    async def get_token_meta(self, token_address: str) -> dict | None:
        """Get token metadata (name, symbol, decimals, supply, etc.)."""
        try:
            url = f"{BASE_URL}/token/meta"
            data = await self.fetch(url, params={"address": token_address})
            return data.get("data") if data else None
        except Exception as e:
            logger.error("solscan.token_meta_failed", address=token_address, error=str(e))
            return None

    async def get_token_holders(
        self, token_address: str, page: int = 1, page_size: int = 40
    ) -> list[dict]:
        """Get top token holders."""
        try:
            url = f"{BASE_URL}/token/holders"
            data = await self.fetch(
                url,
                params={"address": token_address, "page": page, "page_size": page_size},
            )
            return data.get("data", {}).get("items", []) if data else []
        except Exception as e:
            logger.error("solscan.holders_failed", address=token_address, error=str(e))
            return []

    async def get_token_transfers(
        self, token_address: str, page: int = 1, page_size: int = 40
    ) -> list[dict]:
        """Get recent token transfers."""
        try:
            url = f"{BASE_URL}/token/transfer"
            data = await self.fetch(
                url,
                params={"address": token_address, "page": page, "page_size": page_size},
            )
            return data.get("data", {}).get("items", []) if data else []
        except Exception as e:
            logger.error("solscan.transfers_failed", address=token_address, error=str(e))
            return []

    async def get_token_markets(self, token_address: str) -> list[dict]:
        """Get token market/DEX listing data."""
        try:
            url = f"{BASE_URL}/token/markets"
            data = await self.fetch(url, params={"address": token_address})
            return data.get("data", []) if data else []
        except Exception as e:
            logger.error("solscan.markets_failed", address=token_address, error=str(e))
            return []

    async def get_account_tokens(self, wallet_address: str, page: int = 1, page_size: int = 40) -> list[dict]:
        """Get all SPL tokens held by a wallet (for whale tracking)."""
        try:
            url = f"{BASE_URL}/account/token-accounts"
            data = await self.fetch(
                url,
                params={"address": wallet_address, "page": page, "page_size": page_size},
            )
            return data.get("data", []) if data else []
        except Exception as e:
            logger.error("solscan.account_tokens_failed", address=wallet_address, error=str(e))
            return []

    async def collect(self, **kwargs) -> list[dict]:
        """Collect on-chain data from Solscan."""
        if not self.is_configured():
            logger.warning("solscan.skipped", reason="API key not configured")
            return []

        token_address = kwargs.get("token_address", "")
        if not token_address:
            return []

        results = []
        meta = await self.get_token_meta(token_address)
        if meta:
            results.append({"type": "token_meta", "data": meta})

        holders = await self.get_token_holders(token_address)
        if holders:
            results.append({"type": "holders", "data": holders})

        markets = await self.get_token_markets(token_address)
        if markets:
            results.append({"type": "markets", "data": markets})

        return results

    def normalize_to_project(self, meta: dict) -> dict:
        """Normalize Solscan token meta to project format."""
        return {
            "name": meta.get("name", ""),
            "symbol": meta.get("symbol"),
            "slug": f"solscan-{meta.get('address', '')}",
            "contract_address": meta.get("address"),
            "blockchain": "solana",
            "logo_url": meta.get("icon"),
            "source": "solscan",
            "extra_data": {
                "decimals": meta.get("decimals"),
                "supply": meta.get("supply"),
                "holder_count": meta.get("holder"),
            },
        }

    def normalize_to_onchain(self, meta: dict, holders: list[dict] | None = None) -> dict:
        """Normalize Solscan data to OnchainData format."""
        top_holder_pct = 0.0
        if holders:
            total_supply = float(meta.get("supply", 1)) or 1
            for holder in holders[:10]:
                amount = float(holder.get("amount", 0))
                decimals = int(holder.get("decimals", meta.get("decimals", 9)))
                top_holder_pct += (amount / (10**decimals)) / total_supply * 100

        return {
            "holders_count": meta.get("holder"),
            "top_10_holder_pct": round(top_holder_pct, 2) if holders else None,
            "blockchain": "solana",
            "source": "solscan",
            "extra_data": {
                "decimals": meta.get("decimals"),
                "supply": meta.get("supply"),
                "market_count": meta.get("market"),
            },
        }
