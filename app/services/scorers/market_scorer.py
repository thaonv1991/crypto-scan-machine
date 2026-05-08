"""Engine 2: Market Score.

Evaluates market health based on price data, volume, liquidity, and market cap.
Higher scores indicate strong market fundamentals with good liquidity and volume.
"""

import structlog

from app.services.scorers.base import BaseScorer

logger = structlog.get_logger()


class MarketScorer(BaseScorer):
    """Scores based on market data.

    Sub-scores:
    - liquidity (0-25): Liquidity depth relative to market cap
    - volume (0-25): Trading volume health
    - price_action (0-25): Price momentum and stability
    - market_cap (0-25): Market capitalization tier
    """

    engine_name = "engine2_market"

    def calculate(self, data: dict) -> dict:
        try:
            liquidity_score = self._score_liquidity(data)
            volume_score = self._score_volume(data)
            price_score = self._score_price_action(data)
            mcap_score = self._score_market_cap(data)

            total = self.clamp(
                liquidity_score + volume_score + price_score + mcap_score
            )

            return {
                "score": round(total, 2),
                "breakdown": {
                    "liquidity": round(liquidity_score, 2),
                    "volume": round(volume_score, 2),
                    "price_action": round(price_score, 2),
                    "market_cap": round(mcap_score, 2),
                },
            }
        except Exception as e:
            logger.error("scorer.market_failed", error=str(e))
            return {"score": 0.0, "breakdown": {}}

    def _score_liquidity(self, data: dict) -> float:
        """Score based on liquidity depth."""
        liquidity = data.get("liquidity_usd", 0) or 0
        market_cap = data.get("market_cap", 0) or 0

        if liquidity <= 0:
            return 0.0

        base = self.normalize_log(liquidity, 1000, 100_000_000)
        score = base * 0.20

        if market_cap > 0:
            ratio = liquidity / market_cap
            if ratio >= 0.1:
                score += 5.0
            elif ratio >= 0.05:
                score += 3.0
            elif ratio >= 0.01:
                score += 1.0

        return min(25.0, score)

    def _score_volume(self, data: dict) -> float:
        """Score based on 24h trading volume."""
        volume = data.get("volume_24h", 0) or 0
        market_cap = data.get("market_cap", 0) or 0

        if volume <= 0:
            return 0.0

        base = self.normalize_log(volume, 1000, 1_000_000_000)
        score = base * 0.18

        if market_cap > 0:
            vol_mcap_ratio = volume / market_cap
            if 0.05 <= vol_mcap_ratio <= 0.5:
                score += 7.0
            elif 0.01 <= vol_mcap_ratio < 0.05:
                score += 4.0
            elif vol_mcap_ratio > 0.5:
                score += 2.0

        buy_count = data.get("buy_count", 0) or 0
        sell_count = data.get("sell_count", 0) or 0
        total_trades = buy_count + sell_count
        if total_trades > 0:
            buy_ratio = buy_count / total_trades
            if 0.4 <= buy_ratio <= 0.65:
                score += 2.0
            elif buy_ratio > 0.65:
                score += 1.0

        return min(25.0, score)

    def _score_price_action(self, data: dict) -> float:
        """Score based on price momentum and stability."""
        price = data.get("price_usd", 0) or 0
        if price <= 0:
            return 0.0

        score = 5.0

        change_1h = data.get("price_change_1h") or 0
        change_24h = data.get("price_change_24h") or 0
        change_7d = data.get("price_change_7d") or 0

        if -5 <= change_1h <= 10:
            score += 3.0
        elif -15 <= change_1h <= 30:
            score += 1.0

        if -10 <= change_24h <= 20:
            score += 5.0
        elif 20 < change_24h <= 50:
            score += 3.0
        elif change_24h > 50:
            score += 1.0
        elif -20 <= change_24h < -10:
            score += 2.0

        if -15 <= change_7d <= 30:
            score += 5.0
        elif 30 < change_7d <= 100:
            score += 3.0
        elif change_7d > 100:
            score += 1.0
        elif -30 <= change_7d < -15:
            score += 2.0

        vol_change = data.get("volume_change_pct") or 0
        if vol_change > 50:
            score += 2.0
        elif vol_change > 20:
            score += 1.0

        return min(25.0, score)

    def _score_market_cap(self, data: dict) -> float:
        """Score based on market cap tier."""
        market_cap = data.get("market_cap", 0) or 0
        fdv = data.get("fdv", 0) or 0

        if market_cap <= 0 and fdv <= 0:
            return 2.0

        effective_cap = market_cap if market_cap > 0 else fdv
        score = self.normalize_log(effective_cap, 10_000, 10_000_000_000)
        tier_score = score * 0.20

        if market_cap > 0 and fdv > 0 and fdv > market_cap:
            mcap_fdv_ratio = market_cap / fdv
            if mcap_fdv_ratio >= 0.7:
                tier_score += 5.0
            elif mcap_fdv_ratio >= 0.4:
                tier_score += 3.0
            elif mcap_fdv_ratio >= 0.2:
                tier_score += 1.0

        return min(25.0, tier_score)
