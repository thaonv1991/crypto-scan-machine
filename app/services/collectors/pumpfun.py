"""
Pump.fun Collector - New token launches on Solana via Pump.fun.
No API key required - uses public REST API.

Pump.fun is the largest Solana memecoin launchpad.

Endpoints used:
- GET /coins - List recently created coins
- GET /coins/{mint} - Get coin details
- GET /coins/king-of-the-hill - Get trending coin
"""

import structlog

from app.services.collectors.base import BaseCollector

logger = structlog.get_logger()

BASE_URL = "https://frontend-api-v3.pump.fun"


class PumpFunCollector(BaseCollector):
    """Collect new token launches from Pump.fun (Solana memecoin launchpad)."""

    source_name = "pumpfun"
    rate_limit_name = "pumpfun"

    async def get_latest_coins(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """Get recently created coins on Pump.fun."""
        url = f"{BASE_URL}/coins"
        try:
            data = await self.fetch(
                url,
                params={
                    "limit": limit,
                    "offset": offset,
                    "sort": "created_timestamp",
                    "order": "DESC",
                    "includeNsfw": "false",
                },
            )
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error("pumpfun.latest_coins_failed", error=str(e))
            return []

    async def get_coin_details(self, mint_address: str) -> dict | None:
        """Get detailed info for a specific Pump.fun coin."""
        url = f"{BASE_URL}/coins/{mint_address}"
        try:
            data = await self.fetch(url)
            return data if isinstance(data, dict) else None
        except Exception as e:
            logger.error("pumpfun.coin_details_failed", mint=mint_address, error=str(e))
            return None

    async def get_king_of_the_hill(self) -> dict | None:
        """Get the current trending/top coin on Pump.fun."""
        url = f"{BASE_URL}/coins/king-of-the-hill"
        try:
            data = await self.fetch(url)
            return data if isinstance(data, dict) else None
        except Exception as e:
            logger.error("pumpfun.koth_failed", error=str(e))
            return None

    async def get_coin_trades(self, mint_address: str, limit: int = 50, offset: int = 0) -> list[dict]:
        """Get recent trades for a Pump.fun coin."""
        url = f"{BASE_URL}/trades/latest"
        try:
            data = await self.fetch(url, params={"mint": mint_address, "limit": limit, "offset": offset})
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error("pumpfun.trades_failed", mint=mint_address, error=str(e))
            return []

    async def collect(self, **kwargs) -> list[dict]:
        """Collect new token launches from Pump.fun."""
        mode = kwargs.get("mode", "latest")

        if mode == "latest":
            coins = await self.get_latest_coins()
            return [self.normalize_to_project(c) for c in coins]
        elif mode == "koth":
            coin = await self.get_king_of_the_hill()
            return [self.normalize_to_project(coin)] if coin else []
        elif mode == "details":
            mint = kwargs.get("mint_address", "")
            coin = await self.get_coin_details(mint)
            return [self.normalize_to_project(coin)] if coin else []
        return []

    def normalize_to_project(self, raw: dict) -> dict:
        """Normalize Pump.fun coin data to project format."""
        return {
            "name": raw.get("name", ""),
            "symbol": raw.get("symbol"),
            "slug": f"pumpfun-{raw.get('mint', '')}",
            "contract_address": raw.get("mint"),
            "blockchain": "solana",
            "website": raw.get("website"),
            "description": raw.get("description"),
            "logo_url": raw.get("image_uri"),
            "twitter_url": raw.get("twitter"),
            "telegram_url": raw.get("telegram"),
            "source": "pumpfun",
            "extra_data": {
                "bonding_curve": raw.get("bonding_curve"),
                "associated_bonding_curve": raw.get("associated_bonding_curve"),
                "creator": raw.get("creator"),
                "created_timestamp": raw.get("created_timestamp"),
                "market_cap": raw.get("usd_market_cap"),
                "raydium_pool": raw.get("raydium_pool"),
                "is_complete": raw.get("complete", False),
                "virtual_sol_reserves": raw.get("virtual_sol_reserves"),
                "virtual_token_reserves": raw.get("virtual_token_reserves"),
                "total_supply": raw.get("total_supply"),
                "reply_count": raw.get("reply_count"),
            },
        }

    def normalize_to_market_data(self, raw: dict) -> dict:
        """Normalize Pump.fun coin data to market data format."""
        return {
            "price_usd": (
                raw.get("usd_market_cap") / raw.get("total_supply")
                if raw.get("usd_market_cap") and raw.get("total_supply")
                else None
            ),
            "market_cap": raw.get("usd_market_cap"),
            "liquidity_usd": None,
            "source": "pumpfun",
            "extra_data": {
                "bonding_curve": raw.get("bonding_curve"),
                "virtual_sol_reserves": raw.get("virtual_sol_reserves"),
                "virtual_token_reserves": raw.get("virtual_token_reserves"),
                "is_complete": raw.get("complete", False),
            },
        }
