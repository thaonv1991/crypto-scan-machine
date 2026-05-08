"""
Helius Collector - Solana RPC and DAS API.
*** REQUIRES API KEY ***
Free tier: 10 RPS, 100K credits/month
Get API key at: https://dev.helius.xyz/

Provides:
- Enhanced RPC (getAsset, getAssetsByOwner, etc.)
- Webhook-ready transaction parsing
- Token metadata via DAS API
"""

import structlog

from app.core.config import settings
from app.services.collectors.base import BaseCollector

logger = structlog.get_logger()


class HeliusCollector(BaseCollector):
    """Collect Solana data via Helius DAS API and enhanced RPC."""

    source_name = "helius"
    rate_limit_name = "helius"

    def _get_api_key(self) -> str:
        return settings.helius_api_key

    def is_configured(self) -> bool:
        return bool(settings.helius_api_key)

    @property
    def _rpc_url(self) -> str:
        return f"https://mainnet.helius-rpc.com/?api-key={self._get_api_key()}"

    @property
    def _api_url(self) -> str:
        return "https://api.helius.xyz/v0"

    async def _rpc_call(self, method: str, params: list) -> dict | None:
        """Make a JSON-RPC call to Helius enhanced RPC."""
        if not self.is_configured():
            logger.warning("helius.not_configured", hint="Set HELIUS_API_KEY")
            return None

        from app.utils.rate_limiter import rate_limiters

        await rate_limiters.wait_and_acquire(self.rate_limit_name)
        client = await self.get_client()
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        try:
            response = await client.post(self._rpc_url, json=payload)
            response.raise_for_status()
            data = response.json()
            if "error" in data:
                logger.error("helius.rpc_error", method=method, error=data["error"])
                return None
            return data.get("result")
        except Exception as e:
            logger.error("helius.rpc_failed", method=method, error=str(e))
            return None

    async def get_asset(self, asset_id: str) -> dict | None:
        """Get comprehensive asset metadata (DAS API)."""
        return await self._rpc_call("getAsset", [{"id": asset_id}])

    async def get_assets_by_owner(self, owner: str, page: int = 1, limit: int = 100) -> list[dict]:
        """Get all assets owned by a wallet."""
        result = await self._rpc_call(
            "getAssetsByOwner",
            [{"ownerAddress": owner, "page": page, "limit": limit}],
        )
        if result:
            return result.get("items", [])
        return []

    async def get_assets_by_group(self, group_key: str, group_value: str, page: int = 1) -> list[dict]:
        """Get assets by group (e.g., collection)."""
        result = await self._rpc_call(
            "getAssetsByGroup",
            [{"groupKey": group_key, "groupValue": group_value, "page": page}],
        )
        if result:
            return result.get("items", [])
        return []

    async def get_token_metadata(self, mint_address: str) -> dict | None:
        """Get enriched token metadata from Helius API."""
        if not self.is_configured():
            return None

        from app.utils.rate_limiter import rate_limiters

        await rate_limiters.wait_and_acquire(self.rate_limit_name)
        url = f"{self._api_url}/token-metadata"
        client = await self.get_client()
        try:
            response = await client.post(
                url,
                json={"mintAccounts": [mint_address], "includeOffChain": True},
                params={"api-key": self._get_api_key()},
            )
            response.raise_for_status()
            data = response.json()
            return data[0] if data else None
        except Exception as e:
            logger.error("helius.token_metadata_failed", address=mint_address, error=str(e))
            return None

    async def get_parsed_transactions(self, address: str, limit: int = 20) -> list[dict]:
        """Get parsed transaction history for an address."""
        if not self.is_configured():
            return []

        from app.utils.rate_limiter import rate_limiters

        await rate_limiters.wait_and_acquire(self.rate_limit_name)
        url = f"{self._api_url}/addresses/{address}/transactions"
        client = await self.get_client()
        try:
            response = await client.get(
                url,
                params={"api-key": self._get_api_key(), "limit": limit},
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("helius.transactions_failed", address=address, error=str(e))
            return []

    async def collect(self, **kwargs) -> list[dict]:
        """Collect Solana data from Helius."""
        if not self.is_configured():
            logger.warning("helius.skipped", reason="API key not configured")
            return []

        token_address = kwargs.get("token_address", "")
        if not token_address:
            return []

        results = []
        asset = await self.get_asset(token_address)
        if asset:
            results.append({"type": "asset", "data": asset})

        metadata = await self.get_token_metadata(token_address)
        if metadata:
            results.append({"type": "token_metadata", "data": metadata})

        return results

    def normalize_asset_to_project(self, asset: dict) -> dict:
        """Normalize Helius asset data to project format."""
        content = asset.get("content", {})
        metadata = content.get("metadata", {})
        links = content.get("links", {})

        return {
            "name": metadata.get("name", ""),
            "symbol": metadata.get("symbol"),
            "slug": f"helius-{asset.get('id', '')}",
            "contract_address": asset.get("id"),
            "blockchain": "solana",
            "logo_url": content.get("files", [{}])[0].get("uri") if content.get("files") else None,
            "website": links.get("external_url"),
            "source": "helius",
            "extra_data": {
                "token_standard": asset.get("token_info", {}).get("token_program"),
                "supply": asset.get("token_info", {}).get("supply"),
                "decimals": asset.get("token_info", {}).get("decimals"),
                "price_info": asset.get("token_info", {}).get("price_info"),
            },
        }

    def normalize_asset_to_onchain(self, asset: dict) -> dict:
        """Normalize Helius asset data to OnchainData format."""
        ownership = asset.get("ownership", {})
        authorities = asset.get("authorities", [])
        token_info = asset.get("token_info", {})

        is_frozen = ownership.get("frozen", False)
        has_mint_authority = any(
            "mint" in str(a.get("scopes", [])).lower() for a in authorities
        )

        return {
            "is_verified": asset.get("content", {}).get("metadata", {}).get("name") is not None,
            "is_frozen": is_frozen,
            "has_mint_authority": has_mint_authority,
            "blockchain": "solana",
            "source": "helius",
            "extra_data": {
                "owner": ownership.get("owner"),
                "delegate": ownership.get("delegate"),
                "supply": token_info.get("supply"),
                "decimals": token_info.get("decimals"),
                "authorities": authorities,
            },
        }
