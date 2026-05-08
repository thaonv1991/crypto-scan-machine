"""Engine 4: Security Score.

Evaluates on-chain security based on contract analysis, holder distribution,
and red flags. Higher scores indicate safer, more transparent projects.
"""

import structlog

from app.services.scorers.base import BaseScorer

logger = structlog.get_logger()

CRITICAL_FLAGS = {
    "honeypot",
    "is_honeypot",
    "hidden_owner",
    "selfdestruct",
    "external_call",
}

SEVERE_FLAGS = {
    "is_mintable",
    "can_take_back_ownership",
    "transfer_pausable",
    "is_blacklisted",
    "trading_cooldown",
}


class SecurityScorer(BaseScorer):
    """Scores based on on-chain security data.

    Sub-scores:
    - contract (0-30): Contract verification and ownership
    - holder_distribution (0-20): Token holder concentration
    - taxes (0-20): Buy/sell tax levels
    - red_flags (0-30): Penalty based on detected red flags
    """

    engine_name = "engine4_security"

    def calculate(self, data: dict) -> dict:
        try:
            contract_score = self._score_contract(data)
            holder_score = self._score_holders(data)
            tax_score = self._score_taxes(data)
            flag_score = self._score_red_flags(data)

            total = self.clamp(
                contract_score + holder_score + tax_score + flag_score
            )

            return {
                "score": round(total, 2),
                "breakdown": {
                    "contract": round(contract_score, 2),
                    "holder_distribution": round(holder_score, 2),
                    "taxes": round(tax_score, 2),
                    "red_flags": round(flag_score, 2),
                },
            }
        except Exception as e:
            logger.error("scorer.security_failed", error=str(e))
            return {"score": 0.0, "breakdown": {}}

    def _score_contract(self, data: dict) -> float:
        """Score based on contract verification and ownership."""
        score = 0.0

        is_verified = data.get("is_verified")
        if is_verified is True:
            score += 10.0
        elif is_verified is None:
            score += 3.0

        is_renounced = data.get("is_renounced")
        if is_renounced is True:
            score += 8.0
        elif is_renounced is None:
            score += 2.0

        has_proxy = data.get("has_proxy")
        if has_proxy is False:
            score += 5.0
        elif has_proxy is None:
            score += 2.0

        has_mint = data.get("has_mint_function")
        if has_mint is False:
            score += 4.0
        elif has_mint is None:
            score += 1.0

        has_blacklist = data.get("has_blacklist")
        if has_blacklist is False:
            score += 3.0
        elif has_blacklist is None:
            score += 1.0

        return min(30.0, score)

    def _score_holders(self, data: dict) -> float:
        """Score based on token holder distribution."""
        holder_count = data.get("holder_count", 0) or 0
        top10_pct = data.get("top10_holder_pct", 0) or 0
        top50_pct = data.get("top50_holder_pct", 0) or 0

        score = 0.0

        if holder_count >= 10_000:
            score += 8.0
        elif holder_count >= 5_000:
            score += 6.0
        elif holder_count >= 1_000:
            score += 4.0
        elif holder_count >= 100:
            score += 2.0
        elif holder_count > 0:
            score += 1.0

        if top10_pct > 0:
            if top10_pct <= 20:
                score += 6.0
            elif top10_pct <= 40:
                score += 4.0
            elif top10_pct <= 60:
                score += 2.0
            else:
                score += 0.0

        if top50_pct > 0:
            if top50_pct <= 50:
                score += 6.0
            elif top50_pct <= 70:
                score += 4.0
            elif top50_pct <= 85:
                score += 2.0

        return min(20.0, score)

    def _score_taxes(self, data: dict) -> float:
        """Score based on buy/sell tax levels."""
        buy_tax = data.get("buy_tax")
        sell_tax = data.get("sell_tax")

        if buy_tax is None and sell_tax is None:
            return 10.0

        score = 20.0

        if buy_tax is not None:
            if buy_tax > 10:
                score -= 10.0
            elif buy_tax > 5:
                score -= 5.0
            elif buy_tax > 2:
                score -= 2.0

        if sell_tax is not None:
            if sell_tax > 10:
                score -= 10.0
            elif sell_tax > 5:
                score -= 5.0
            elif sell_tax > 2:
                score -= 2.0

        return max(0.0, score)

    def _score_red_flags(self, data: dict) -> float:
        """Score based on detected red flags. Starts at max and deducts."""
        red_flags = data.get("red_flags", [])
        if not red_flags:
            return 30.0

        score = 30.0
        for flag in red_flags:
            flag_type = flag.get("flag_type", "")
            severity = flag.get("severity", "medium")
            is_active = flag.get("is_active", True)

            if not is_active:
                continue

            if flag_type in CRITICAL_FLAGS or severity == "critical":
                score -= 15.0
            elif flag_type in SEVERE_FLAGS or severity == "high":
                score -= 8.0
            elif severity == "medium":
                score -= 4.0
            else:
                score -= 2.0

        return max(0.0, score)
