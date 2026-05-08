"""
TokenSniffer Collector - Token security and scam detection.
No API key required for basic checks (public endpoint).
Pro API available at: https://tokensniffer.com/TokenSnifferAPI

Provides:
- Scam score / risk assessment
- Contract analysis (honeypot, rug pull indicators)
- Similar token detection (clone/copy detection)
"""

import structlog

from app.services.collectors.base import BaseCollector

logger = structlog.get_logger()

BASE_URL = "https://tokensniffer.com/api/v2"

CHAIN_IDS = {
    "ethereum": 1,
    "bsc": 56,
    "polygon": 137,
    "arbitrum": 42161,
    "base": 8453,
    "avalanche": 43114,
}


class TokenSnifferCollector(BaseCollector):
    """Collect token security scores from TokenSniffer."""

    source_name = "tokensniffer"
    rate_limit_name = "tokensniffer"

    async def get_token_score(self, contract_address: str, chain_id: int = 1) -> dict | None:
        """Get security score and risk analysis for a token.

        Args:
            contract_address: Token contract address
            chain_id: Blockchain chain ID (1=ETH, 56=BSC, etc.)
        """
        url = f"{BASE_URL}/tokens/{chain_id}/{contract_address}"
        try:
            data = await self.fetch(url)
            return data if isinstance(data, dict) else None
        except Exception as e:
            logger.error(
                "tokensniffer.score_failed",
                address=contract_address,
                chain_id=chain_id,
                error=str(e),
            )
            return None

    async def collect(self, **kwargs) -> list[dict]:
        """Collect token security data from TokenSniffer."""
        contract_address = kwargs.get("contract_address", "")
        blockchain = kwargs.get("blockchain", "ethereum")

        if not contract_address:
            return []

        chain_id = CHAIN_IDS.get(blockchain, 1)
        score_data = await self.get_token_score(contract_address, chain_id)

        if score_data:
            return [self.normalize_to_security(score_data, blockchain)]
        return []

    def normalize_to_security(self, raw: dict, blockchain: str) -> dict:
        """Normalize TokenSniffer data to security/red-flag format."""
        score = raw.get("score", 0)
        exploits = raw.get("exploits", []) or []
        swap_analysis = raw.get("swap_simulation", {}) or {}

        is_honeypot = swap_analysis.get("is_honeypot", False)
        buy_tax = swap_analysis.get("buy_tax")
        sell_tax = swap_analysis.get("sell_tax")

        red_flags = []
        for exploit in exploits:
            red_flags.append({
                "type": exploit.get("type", "unknown"),
                "description": exploit.get("description", ""),
                "severity": exploit.get("severity", "medium"),
            })

        if is_honeypot:
            red_flags.append({
                "type": "honeypot",
                "description": "Token appears to be a honeypot - sells may be blocked",
                "severity": "critical",
            })

        if sell_tax and float(sell_tax) > 10:
            red_flags.append({
                "type": "high_sell_tax",
                "description": f"High sell tax detected: {sell_tax}%",
                "severity": "high",
            })

        return {
            "security_score": score,
            "is_honeypot": is_honeypot,
            "buy_tax": buy_tax,
            "sell_tax": sell_tax,
            "red_flags": red_flags,
            "blockchain": blockchain,
            "source": "tokensniffer",
            "extra_data": {
                "similar_tokens": raw.get("similar_tokens", []),
                "is_flagged": raw.get("is_flagged", False),
                "deployer": raw.get("deployer"),
                "contract_analysis": raw.get("contract_analysis"),
                "permissions": raw.get("permissions", {}),
            },
        }
