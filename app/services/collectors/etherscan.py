"""
Etherscan Collector - Engine 4 (On-chain Data)
*** REQUIRES API KEY ***
Free tier: 5 calls/sec, 100k calls/day
Get API key at: https://etherscan.io/myapikey

Endpoints used:
- GET /api?module=account&action=tokentx - Token transfers
- GET /api?module=contract&action=getsourcecode - Contract verification
- GET /api?module=token&action=tokenholderlist - Token holders

Supported chains (with their respective explorers):
- Ethereum: api.etherscan.io
- BSC: api.bscscan.com
- Polygon: api.polygonscan.com
- Arbitrum: api.arbiscan.io
- Base: api.basescan.org
"""

import structlog

from app.core.config import settings
from app.services.collectors.base import BaseCollector

logger = structlog.get_logger()

CHAIN_API_URLS = {
    "ethereum": "https://api.etherscan.io",
    "bsc": "https://api.bscscan.com",
    "polygon": "https://api.polygonscan.com",
    "arbitrum": "https://api.arbiscan.io",
    "base": "https://api.basescan.org",
}


class EtherscanCollector(BaseCollector):
    """Collect on-chain data from Etherscan-compatible APIs.

    REQUIRES: ETHERSCAN_API_KEY environment variable.
    Get your free API key at https://etherscan.io/myapikey
    """

    source_name = "etherscan"
    rate_limit_name = "etherscan"

    def _get_api_url(self, blockchain: str) -> str:
        return CHAIN_API_URLS.get(blockchain, CHAIN_API_URLS["ethereum"])

    def _get_api_key(self) -> str:
        return settings.etherscan_api_key

    def is_configured(self) -> bool:
        return bool(settings.etherscan_api_key)

    async def get_contract_source(self, contract_address: str, blockchain: str = "ethereum") -> dict | None:
        """Check if a contract is verified and get source code info."""
        if not self.is_configured():
            logger.warning("etherscan.not_configured", hint="Set ETHERSCAN_API_KEY")
            return None

        base_url = self._get_api_url(blockchain)
        url = f"{base_url}/api"
        params = {
            "module": "contract",
            "action": "getsourcecode",
            "address": contract_address,
            "apikey": self._get_api_key(),
        }
        try:
            data = await self.fetch(url, params=params)
            results = data.get("result", [])
            return results[0] if results else None
        except Exception as e:
            logger.error("etherscan.contract_source_failed", address=contract_address, error=str(e))
            return None

    async def get_token_transfers(
        self,
        contract_address: str,
        blockchain: str = "ethereum",
        page: int = 1,
        offset: int = 100,
    ) -> list[dict]:
        """Get recent token transfers."""
        if not self.is_configured():
            logger.warning("etherscan.not_configured")
            return []

        base_url = self._get_api_url(blockchain)
        url = f"{base_url}/api"
        params = {
            "module": "account",
            "action": "tokentx",
            "contractaddress": contract_address,
            "page": str(page),
            "offset": str(offset),
            "sort": "desc",
            "apikey": self._get_api_key(),
        }
        try:
            data = await self.fetch(url, params=params)
            results = data.get("result", [])
            return results if isinstance(results, list) else []
        except Exception as e:
            logger.error("etherscan.token_transfers_failed", address=contract_address, error=str(e))
            return []

    async def get_token_info(self, contract_address: str, blockchain: str = "ethereum") -> dict | None:
        """Get token supply info."""
        if not self.is_configured():
            return None

        base_url = self._get_api_url(blockchain)
        url = f"{base_url}/api"
        params = {
            "module": "stats",
            "action": "tokensupply",
            "contractaddress": contract_address,
            "apikey": self._get_api_key(),
        }
        try:
            data = await self.fetch(url, params=params)
            return {"total_supply": data.get("result")}
        except Exception as e:
            logger.error("etherscan.token_info_failed", address=contract_address, error=str(e))
            return None

    async def collect(self, **kwargs) -> list[dict]:
        """Collect on-chain data from Etherscan."""
        if not self.is_configured():
            logger.warning("etherscan.skipped", reason="API key not configured")
            return []

        contract_address = kwargs.get("contract_address", "")
        blockchain = kwargs.get("blockchain", "ethereum")

        results = []
        source = await self.get_contract_source(contract_address, blockchain)
        if source:
            results.append({"type": "contract_source", "data": source})

        transfers = await self.get_token_transfers(contract_address, blockchain)
        if transfers:
            results.append({"type": "transfers", "data": transfers})

        return results

    def normalize_contract_to_onchain(self, source: dict, blockchain: str) -> dict:
        """Normalize Etherscan contract data to OnchainData format."""
        is_verified = source.get("SourceCode", "") != ""
        return {
            "is_verified": is_verified,
            "is_renounced": None,
            "has_proxy": source.get("Proxy") == "1",
            "blockchain": blockchain,
            "source": "etherscan",
            "extra_data": {
                "compiler_version": source.get("CompilerVersion"),
                "optimization_used": source.get("OptimizationUsed"),
                "contract_name": source.get("ContractName"),
                "implementation": source.get("Implementation"),
            },
        }
