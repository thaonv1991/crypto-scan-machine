"""
GoPlus Labs Collector - Engine 4 (On-chain Security Analysis)
Free tier: 100 calls/minute, no API key required.

Endpoints used:
- GET /api/v1/token_security/{chain_id}?contract_addresses=ADDR - Token security info
- GET /api/v1/address_security/{address}?chain_id=ID - Address security check

Chain IDs:
- 1: Ethereum
- 56: BSC
- 137: Polygon
- 42161: Arbitrum
- 43114: Avalanche
- 8453: Base
"""

import structlog

from app.services.collectors.base import BaseCollector

logger = structlog.get_logger()

BASE_URL = "https://api.gopluslabs.io"

BLOCKCHAIN_TO_CHAIN_ID = {
    "ethereum": "1",
    "bsc": "56",
    "polygon": "137",
    "arbitrum": "42161",
    "avalanche": "43114",
    "base": "8453",
}

CHAIN_ID_TO_BLOCKCHAIN = {v: k for k, v in BLOCKCHAIN_TO_CHAIN_ID.items()}


class GoPlusCollector(BaseCollector):
    """Collect token security data from GoPlus Labs free API."""

    source_name = "goplus"
    rate_limit_name = "goplus"

    async def get_token_security(self, chain_id: str, contract_address: str) -> dict | None:
        """Get token security information for a contract address."""
        url = f"{BASE_URL}/api/v1/token_security/{chain_id}"
        params = {"contract_addresses": contract_address.lower()}
        try:
            data = await self.fetch(url, params=params)
            if data.get("code") != 1:
                logger.warning(
                    "goplus.token_security_error",
                    code=data.get("code"),
                    message=data.get("message"),
                )
                return None

            result = data.get("result", {})
            return result.get(contract_address.lower())
        except Exception as e:
            logger.error(
                "goplus.token_security_failed",
                chain_id=chain_id,
                contract_address=contract_address,
                error=str(e),
            )
            return None

    async def get_address_security(self, address: str, chain_id: str = "1") -> dict | None:
        """Check if an address is malicious."""
        url = f"{BASE_URL}/api/v1/address_security/{address}"
        params = {"chain_id": chain_id}
        try:
            data = await self.fetch(url, params=params)
            if data.get("code") != 1:
                return None
            return data.get("result")
        except Exception as e:
            logger.error("goplus.address_security_failed", address=address, error=str(e))
            return None

    async def collect(self, **kwargs) -> list[dict]:
        """Collect security data for given tokens."""
        blockchain = kwargs.get("blockchain", "ethereum")
        contract_addresses = kwargs.get("contract_addresses", [])
        chain_id = BLOCKCHAIN_TO_CHAIN_ID.get(blockchain, "1")

        results = []
        for addr in contract_addresses:
            data = await self.get_token_security(chain_id, addr)
            if data:
                results.append({"contract_address": addr, "chain_id": chain_id, "security": data})

        return results

    def normalize_to_onchain_data(self, security: dict, blockchain: str) -> dict:
        """Normalize GoPlus security data to our OnchainData format."""
        return {
            "holder_count": _safe_int(security.get("holder_count")),
            "total_supply": _safe_float(security.get("total_supply")),
            "top10_holder_pct": _calc_top_holder_pct(security.get("holders", []), 10),
            "is_verified": security.get("is_open_source") == "1",
            "is_renounced": security.get("can_take_back_ownership") == "0",
            "has_proxy": security.get("is_proxy") == "1",
            "has_mint_function": security.get("is_mintable") == "1",
            "has_blacklist": security.get("is_blacklisted") == "1",
            "buy_tax": _safe_float(security.get("buy_tax")),
            "sell_tax": _safe_float(security.get("sell_tax")),
            "liquidity_locked": None,
            "blockchain": blockchain,
            "source": "goplus",
            "extra_data": {
                "is_honeypot": security.get("is_honeypot"),
                "is_open_source": security.get("is_open_source"),
                "is_proxy": security.get("is_proxy"),
                "is_mintable": security.get("is_mintable"),
                "can_take_back_ownership": security.get("can_take_back_ownership"),
                "owner_change_balance": security.get("owner_change_balance"),
                "hidden_owner": security.get("hidden_owner"),
                "selfdestruct": security.get("selfdestruct"),
                "external_call": security.get("external_call"),
                "anti_whale_modifiable": security.get("anti_whale_modifiable"),
                "trading_cooldown": security.get("trading_cooldown"),
                "transfer_pausable": security.get("transfer_pausable"),
                "personal_slippage_modifiable": security.get("personal_slippage_modifiable"),
                "is_anti_whale": security.get("is_anti_whale"),
                "trust_list": security.get("trust_list"),
                "is_whitelisted": security.get("is_whitelisted"),
                "lp_holders": security.get("lp_holders"),
                "lp_total_supply": security.get("lp_total_supply"),
            },
        }

    def detect_red_flags(self, security: dict, contract_address: str) -> list[dict]:
        """Detect red flags from GoPlus security data."""
        flags = []

        if security.get("is_honeypot") == "1":
            flags.append({
                "flag_type": "honeypot",
                "severity": "critical",
                "title": "Token detected as honeypot",
                "description": "GoPlus detected this token as a honeypot - users may not be able to sell.",
                "detected_by": "goplus",
                "engine": "engine4",
                "confidence": 0.95,
            })

        if security.get("is_open_source") == "0":
            flags.append({
                "flag_type": "unverified_contract",
                "severity": "high",
                "title": "Contract source code not verified",
                "description": "The contract source code is not verified on the block explorer.",
                "detected_by": "goplus",
                "engine": "engine4",
                "confidence": 0.9,
            })

        if security.get("is_mintable") == "1":
            flags.append({
                "flag_type": "mintable",
                "severity": "high",
                "title": "Token has mint function",
                "description": "The contract owner can mint additional tokens, potentially diluting value.",
                "detected_by": "goplus",
                "engine": "engine4",
                "confidence": 0.85,
            })

        buy_tax = _safe_float(security.get("buy_tax"))
        sell_tax = _safe_float(security.get("sell_tax"))
        if buy_tax is not None and buy_tax > 0.1:
            flags.append({
                "flag_type": "high_buy_tax",
                "severity": "high",
                "title": f"High buy tax: {buy_tax * 100:.1f}%",
                "description": f"Buy tax is {buy_tax * 100:.1f}%, which is unusually high.",
                "detected_by": "goplus",
                "engine": "engine4",
                "confidence": 0.9,
            })
        if sell_tax is not None and sell_tax > 0.1:
            flags.append({
                "flag_type": "high_sell_tax",
                "severity": "critical",
                "title": f"High sell tax: {sell_tax * 100:.1f}%",
                "description": f"Sell tax is {sell_tax * 100:.1f}%, which is unusually high.",
                "detected_by": "goplus",
                "engine": "engine4",
                "confidence": 0.9,
            })

        if security.get("can_take_back_ownership") == "1":
            flags.append({
                "flag_type": "ownership_takeback",
                "severity": "high",
                "title": "Owner can take back ownership",
                "description": "The contract owner can reclaim ownership after renouncing.",
                "detected_by": "goplus",
                "engine": "engine4",
                "confidence": 0.85,
            })

        if security.get("hidden_owner") == "1":
            flags.append({
                "flag_type": "hidden_owner",
                "severity": "medium",
                "title": "Hidden owner detected",
                "description": "The contract has a hidden owner mechanism.",
                "detected_by": "goplus",
                "engine": "engine4",
                "confidence": 0.8,
            })

        if security.get("selfdestruct") == "1":
            flags.append({
                "flag_type": "selfdestruct",
                "severity": "critical",
                "title": "Contract can self-destruct",
                "description": "The contract contains a self-destruct function.",
                "detected_by": "goplus",
                "engine": "engine4",
                "confidence": 0.95,
            })

        if security.get("transfer_pausable") == "1":
            flags.append({
                "flag_type": "transfer_pausable",
                "severity": "medium",
                "title": "Token transfers can be paused",
                "description": "The contract owner can pause all token transfers.",
                "detected_by": "goplus",
                "engine": "engine4",
                "confidence": 0.8,
            })

        return flags


def _safe_float(value: str | float | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _safe_int(value: str | int | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _calc_top_holder_pct(holders: list[dict], top_n: int) -> float | None:
    """Calculate the percentage held by top N holders."""
    if not holders:
        return None
    sorted_holders = sorted(holders, key=lambda h: float(h.get("percent", 0)), reverse=True)
    top = sorted_holders[:top_n]
    total_pct = sum(float(h.get("percent", 0)) for h in top)
    return total_pct
