"""
BSCScan Collector - On-chain data for BNB Smart Chain.
*** REQUIRES API KEY ***
Free tier: 5 calls/sec, 100k calls/day
Get API key at: https://bscscan.com/myapikey

Uses same API format as Etherscan (BSCScan is an Etherscan fork).
"""

import structlog

from app.core.config import settings
from app.services.collectors.base import BaseCollector

logger = structlog.get_logger()

BASE_URL = "https://api.bscscan.com/api"


class BSCScanCollector(BaseCollector):
    """Collect on-chain data from BSCScan for BNB Smart Chain tokens."""

    source_name = "bscscan"
    rate_limit_name = "bscscan"

    def _get_api_key(self) -> str:
        return settings.bscscan_api_key

    def is_configured(self) -> bool:
        return bool(settings.bscscan_api_key)

    async def get_contract_source(self, contract_address: str) -> dict | None:
        """Check if a contract is verified and get source code info."""
        if not self.is_configured():
            logger.warning("bscscan.not_configured", hint="Set BSCSCAN_API_KEY")
            return None

        params = {
            "module": "contract",
            "action": "getsourcecode",
            "address": contract_address,
            "apikey": self._get_api_key(),
        }
        try:
            data = await self.fetch(BASE_URL, params=params)
            results = data.get("result", [])
            return results[0] if results else None
        except Exception as e:
            logger.error("bscscan.contract_source_failed", address=contract_address, error=str(e))
            return None

    async def get_token_transfers(
        self,
        contract_address: str,
        page: int = 1,
        offset: int = 100,
    ) -> list[dict]:
        """Get recent BEP-20 token transfers."""
        if not self.is_configured():
            return []

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
            data = await self.fetch(BASE_URL, params=params)
            results = data.get("result", [])
            return results if isinstance(results, list) else []
        except Exception as e:
            logger.error("bscscan.token_transfers_failed", address=contract_address, error=str(e))
            return []

    async def get_token_supply(self, contract_address: str) -> str | None:
        """Get total supply of a BEP-20 token."""
        if not self.is_configured():
            return None

        params = {
            "module": "stats",
            "action": "tokensupply",
            "contractaddress": contract_address,
            "apikey": self._get_api_key(),
        }
        try:
            data = await self.fetch(BASE_URL, params=params)
            return data.get("result")
        except Exception as e:
            logger.error("bscscan.token_supply_failed", address=contract_address, error=str(e))
            return None

    async def get_bnb_balance(self, address: str) -> str | None:
        """Get BNB balance for an address."""
        if not self.is_configured():
            return None

        params = {
            "module": "account",
            "action": "balance",
            "address": address,
            "tag": "latest",
            "apikey": self._get_api_key(),
        }
        try:
            data = await self.fetch(BASE_URL, params=params)
            return data.get("result")
        except Exception as e:
            logger.error("bscscan.balance_failed", address=address, error=str(e))
            return None

    async def get_token_holders(self, contract_address: str, page: int = 1, offset: int = 50) -> list[dict]:
        """Get top token holders (requires BSCScan Pro, falls back gracefully)."""
        if not self.is_configured():
            return []

        params = {
            "module": "token",
            "action": "tokenholderlist",
            "contractaddress": contract_address,
            "page": str(page),
            "offset": str(offset),
            "apikey": self._get_api_key(),
        }
        try:
            data = await self.fetch(BASE_URL, params=params)
            results = data.get("result", [])
            return results if isinstance(results, list) else []
        except Exception as e:
            logger.error("bscscan.holders_failed", address=contract_address, error=str(e))
            return []

    async def get_internal_txns(self, contract_address: str, page: int = 1, offset: int = 50) -> list[dict]:
        """Get internal transactions for a contract."""
        if not self.is_configured():
            return []

        params = {
            "module": "account",
            "action": "txlistinternal",
            "address": contract_address,
            "page": str(page),
            "offset": str(offset),
            "sort": "desc",
            "apikey": self._get_api_key(),
        }
        try:
            data = await self.fetch(BASE_URL, params=params)
            results = data.get("result", [])
            return results if isinstance(results, list) else []
        except Exception as e:
            logger.error("bscscan.internal_txns_failed", address=contract_address, error=str(e))
            return []

    async def collect(self, **kwargs) -> list[dict]:
        """Collect on-chain data from BSCScan."""
        if not self.is_configured():
            logger.warning("bscscan.skipped", reason="API key not configured")
            return []

        contract_address = kwargs.get("contract_address", "")
        if not contract_address:
            return []

        results = []
        source = await self.get_contract_source(contract_address)
        if source:
            results.append({"type": "contract_source", "data": source})

        transfers = await self.get_token_transfers(contract_address)
        if transfers:
            results.append({"type": "transfers", "data": transfers})

        return results

    def normalize_contract_to_onchain(self, source: dict) -> dict:
        """Normalize BSCScan contract data to OnchainData format."""
        is_verified = source.get("SourceCode", "") != ""
        return {
            "is_verified": is_verified,
            "is_renounced": None,
            "has_proxy": source.get("Proxy") == "1",
            "blockchain": "bsc",
            "source": "bscscan",
            "extra_data": {
                "compiler_version": source.get("CompilerVersion"),
                "optimization_used": source.get("OptimizationUsed"),
                "contract_name": source.get("ContractName"),
                "implementation": source.get("Implementation"),
            },
        }

    def normalize_transfers_to_whale_activity(self, transfers: list[dict], min_value_usd: float = 50000) -> list[dict]:
        """Extract potential whale activities from token transfers."""
        whales = []
        for tx in transfers:
            value = int(tx.get("value", "0")) / (10 ** int(tx.get("tokenDecimal", "18")))
            if value > 0:
                whales.append({
                    "tx_hash": tx.get("hash"),
                    "from_address": tx.get("from"),
                    "to_address": tx.get("to"),
                    "amount": value,
                    "token_symbol": tx.get("tokenSymbol"),
                    "blockchain": "bsc",
                    "block_number": tx.get("blockNumber"),
                    "timestamp": tx.get("timeStamp"),
                    "source": "bscscan",
                })
        return whales
