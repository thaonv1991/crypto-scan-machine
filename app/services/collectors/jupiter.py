"""
Jupiter Collector - Solana DEX aggregator.
Requires API key for price and swap endpoints.
Get API key at: https://portal.jup.ag
"""

import os

import structlog

from app.services.collectors.base import BaseCollector

logger = structlog.get_logger()

BASE_URL = "https://api.jup.ag"


class JupiterCollector(BaseCollector):
    """Collector for Jupiter Solana DEX data. Requires JUP_API_KEY."""

    source_name = "jupiter"
    rate_limit_name = "jupiter"

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("JUP_API_KEY", "")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def fetch(self, url: str, params: dict | None = None) -> dict:
        if not self.is_configured():
            logger.warning("jupiter.not_configured")
            return {}
        from app.utils.rate_limiter import rate_limiters

        await rate_limiters.wait_and_acquire(self.rate_limit_name)
        client = await self.get_client()
        response = await client.get(
            url,
            params=params,
            headers={"x-api-key": self.api_key, "Accept": "application/json"},
        )
        response.raise_for_status()
        return response.json()

    async def collect(self, **kwargs) -> list[dict]:
        if not self.is_configured():
            return []
        token_ids = kwargs.get("token_ids", [])
        if not token_ids:
            return []
        prices = await self.get_prices(token_ids)
        return [self.normalize_price_to_market_data(addr, info) for addr, info in prices.items()]

    async def get_prices(self, token_ids: list[str]) -> dict:
        """Get current prices for Solana tokens by mint address."""
        try:
            ids_str = ",".join(token_ids[:50])
            url = f"{BASE_URL}/price/v3"
            data = await self.fetch(url, params={"ids": ids_str})
            return data if isinstance(data, dict) else {}
        except Exception as e:
            logger.error("jupiter.prices_failed", error=str(e))
            return {}

    async def get_token_list(self) -> list[dict]:
        """Get list of all tradable tokens on Jupiter."""
        try:
            url = f"{BASE_URL}/tokens/v1/all"
            data = await self.fetch(url)
            if isinstance(data, list):
                return data
            return []
        except Exception as e:
            logger.error("jupiter.token_list_failed", error=str(e))
            return []

    async def get_token_info(self, mint: str) -> dict | None:
        """Get token info by mint address."""
        try:
            url = f"{BASE_URL}/tokens/v1/{mint}"
            return await self.fetch(url)
        except Exception as e:
            logger.error("jupiter.token_info_failed", mint=mint, error=str(e))
            return None

    async def get_swap_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = 50,
    ) -> dict | None:
        """Get a swap quote (useful to check token tradability/liquidity)."""
        try:
            url = f"{BASE_URL}/swap/v2/order"
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": amount,
                "slippageBps": slippage_bps,
            }
            return await self.fetch(url, params=params)
        except Exception as e:
            logger.error("jupiter.swap_quote_failed", error=str(e))
            return None

    def normalize_price_to_market_data(self, mint: str, price_info: dict) -> dict:
        """Normalize Jupiter price data to market data format."""
        return {
            "contract_address": mint,
            "price_usd": price_info.get("usdPrice"),
            "volume_24h": None,
            "market_cap": None,
            "liquidity_usd": price_info.get("liquidity"),
            "price_change_24h": price_info.get("priceChange24h"),
            "source": "jupiter",
            "extra_data": {
                "decimals": price_info.get("decimals"),
                "block_id": price_info.get("blockId"),
                "created_at": price_info.get("createdAt"),
            },
        }
