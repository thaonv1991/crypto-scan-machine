"""
Birdeye Collector - Solana and multi-chain token analytics.
Requires API key for all endpoints.
Get API key at: https://bds.birdeye.so (sign up and generate key in account settings)
"""

import os

import structlog

from app.services.collectors.base import BaseCollector

logger = structlog.get_logger()

BASE_URL = "https://public-api.birdeye.so"


class BirdeyeCollector(BaseCollector):
    """Collector for Birdeye token analytics. Requires BIRDEYE_API_KEY."""

    source_name = "birdeye"
    rate_limit_name = "birdeye"

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("BIRDEYE_API_KEY", "")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def fetch(self, url: str, params: dict | None = None, chain: str = "solana") -> dict:
        if not self.is_configured():
            logger.warning("birdeye.not_configured")
            return {}
        from app.utils.rate_limiter import rate_limiters

        await rate_limiters.wait_and_acquire(self.rate_limit_name)
        client = await self.get_client()
        response = await client.get(
            url,
            params=params,
            headers={
                "X-API-KEY": self.api_key,
                "x-chain": chain,
                "Accept": "application/json",
            },
        )
        response.raise_for_status()
        return response.json()

    async def collect(self, **kwargs) -> list[dict]:
        if not self.is_configured():
            return []
        token_address = kwargs.get("token_address")
        if not token_address:
            return []
        overview = await self.get_token_overview(token_address)
        if overview:
            return [self.normalize_to_market_data(overview)]
        return []

    async def get_token_overview(self, address: str, chain: str = "solana") -> dict | None:
        """Get comprehensive token overview (price, volume, trades, supply)."""
        try:
            url = f"{BASE_URL}/defi/token_overview"
            data = await self.fetch(url, params={"address": address}, chain=chain)
            return data.get("data")
        except Exception as e:
            logger.error("birdeye.token_overview_failed", error=str(e))
            return None

    async def get_token_security(self, address: str, chain: str = "solana") -> dict | None:
        """Get token security info (ownership, mintable, etc.)."""
        try:
            url = f"{BASE_URL}/defi/token_security"
            data = await self.fetch(url, params={"address": address}, chain=chain)
            return data.get("data")
        except Exception as e:
            logger.error("birdeye.token_security_failed", error=str(e))
            return None

    async def get_token_creation_info(self, address: str, chain: str = "solana") -> dict | None:
        """Get token creation details (deployer, timestamp)."""
        try:
            url = f"{BASE_URL}/defi/token_creation_info"
            data = await self.fetch(url, params={"address": address}, chain=chain)
            return data.get("data")
        except Exception as e:
            logger.error("birdeye.token_creation_failed", error=str(e))
            return None

    async def get_token_holders(
        self, address: str, chain: str = "solana", offset: int = 0, limit: int = 100
    ) -> list[dict]:
        """Get top token holders."""
        try:
            url = f"{BASE_URL}/defi/v3/token/holder"
            data = await self.fetch(
                url,
                params={"address": address, "offset": offset, "limit": limit},
                chain=chain,
            )
            items = data.get("data", {})
            return items.get("items", []) if isinstance(items, dict) else []
        except Exception as e:
            logger.error("birdeye.holders_failed", error=str(e))
            return []

    async def get_token_trades(
        self, address: str, chain: str = "solana", limit: int = 50
    ) -> list[dict]:
        """Get recent trades for a token."""
        try:
            url = f"{BASE_URL}/defi/txs/token"
            data = await self.fetch(
                url,
                params={"address": address, "limit": limit, "tx_type": "swap"},
                chain=chain,
            )
            items = data.get("data", {})
            return items.get("items", []) if isinstance(items, dict) else []
        except Exception as e:
            logger.error("birdeye.trades_failed", error=str(e))
            return []

    def normalize_to_market_data(self, overview: dict) -> dict:
        """Normalize Birdeye token overview to market data format."""
        return {
            "contract_address": overview.get("address"),
            "name": overview.get("name", ""),
            "symbol": overview.get("symbol", ""),
            "price_usd": overview.get("price"),
            "volume_24h": overview.get("v24hUSD"),
            "market_cap": overview.get("mc"),
            "fdv": overview.get("fdv"),
            "liquidity_usd": overview.get("liquidity"),
            "price_change_1h": overview.get("priceChange1hPercent"),
            "price_change_24h": overview.get("priceChange24hPercent"),
            "source": "birdeye",
            "extra_data": {
                "decimals": overview.get("decimals"),
                "holder_count": overview.get("holder"),
                "unique_wallet_24h": overview.get("uniqueWallet24h"),
                "trade_24h": overview.get("trade24h"),
                "buy_24h": overview.get("buy24h"),
                "sell_24h": overview.get("sell24h"),
                "supply": overview.get("supply"),
                "logo_uri": overview.get("logoURI"),
            },
        }

    def normalize_to_project(self, overview: dict) -> dict:
        """Normalize Birdeye token overview to project format."""
        extensions = overview.get("extensions", {})
        return {
            "name": overview.get("name", ""),
            "symbol": overview.get("symbol"),
            "slug": f"birdeye-{overview.get('address', '')}",
            "contract_address": overview.get("address"),
            "blockchain": "solana",
            "website": extensions.get("website"),
            "twitter_url": extensions.get("twitter"),
            "telegram_url": extensions.get("telegram"),
            "discord_url": extensions.get("discord"),
            "logo_url": overview.get("logoURI"),
            "source": "birdeye",
            "extra_data": {
                "coingecko_id": extensions.get("coingeckoId"),
                "description": extensions.get("description"),
            },
        }
