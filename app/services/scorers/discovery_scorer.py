"""Engine 1: Discovery Score.

Evaluates how a project was discovered and its presence across data sources.
Higher scores indicate projects found by multiple sources, trending, and recently launched.
"""

from datetime import datetime, timezone

import structlog

from app.services.scorers.base import BaseScorer

logger = structlog.get_logger()

SOURCE_WEIGHTS = {
    "dexscreener": 15,
    "coingecko": 20,
    "geckoterminal": 15,
    "defillama": 20,
    "coinmarketcap": 20,
    "birdeye": 10,
    "jupiter": 10,
    "dextools": 10,
}

MAX_SOURCE_SCORE = 50


class DiscoveryScorer(BaseScorer):
    """Scores based on project discovery metadata.

    Sub-scores:
    - source_diversity (0-35): How many data sources list this project
    - recency (0-25): How recently the project was discovered
    - completeness (0-25): How much metadata is available
    - status (0-15): Current monitoring status
    """

    engine_name = "engine1_discovery"

    def calculate(self, data: dict) -> dict:
        try:
            source_score = self._score_source_diversity(data)
            recency_score = self._score_recency(data)
            completeness_score = self._score_completeness(data)
            status_score = self._score_status(data)

            total = self.clamp(
                source_score + recency_score + completeness_score + status_score
            )

            return {
                "score": round(total, 2),
                "breakdown": {
                    "source_diversity": round(source_score, 2),
                    "recency": round(recency_score, 2),
                    "completeness": round(completeness_score, 2),
                    "status": round(status_score, 2),
                },
            }
        except Exception as e:
            logger.error("scorer.discovery_failed", error=str(e))
            return {"score": 0.0, "breakdown": {}}

    def _score_source_diversity(self, data: dict) -> float:
        """Score based on how many data sources list this project."""
        sources = data.get("sources", [])
        if not sources:
            primary = data.get("source", "")
            return SOURCE_WEIGHTS.get(primary, 5) * 35 / MAX_SOURCE_SCORE

        total_weight = sum(SOURCE_WEIGHTS.get(s, 5) for s in sources)
        return min(35.0, total_weight * 35 / MAX_SOURCE_SCORE)

    def _score_recency(self, data: dict) -> float:
        """Score based on how recently the project was discovered."""
        discovered_at = data.get("discovered_at")
        if not discovered_at:
            return 10.0

        if isinstance(discovered_at, str):
            try:
                discovered_at = datetime.fromisoformat(discovered_at)
            except (ValueError, TypeError):
                return 10.0

        if discovered_at.tzinfo is None:
            discovered_at = discovered_at.replace(tzinfo=timezone.utc)

        age_hours = (datetime.now(timezone.utc) - discovered_at).total_seconds() / 3600

        if age_hours < 1:
            return 25.0
        if age_hours < 6:
            return 22.0
        if age_hours < 24:
            return 18.0
        if age_hours < 72:
            return 14.0
        if age_hours < 168:
            return 10.0
        if age_hours < 720:
            return 6.0
        return 3.0

    def _score_completeness(self, data: dict) -> float:
        """Score based on how much metadata is available."""
        fields = [
            "name", "symbol", "contract_address", "blockchain",
            "website", "description", "logo_url", "category",
            "twitter_url", "telegram_url", "discord_url", "github_url",
        ]
        filled = sum(1 for f in fields if data.get(f))
        return (filled / len(fields)) * 25

    def _score_status(self, data: dict) -> float:
        """Score based on current monitoring status."""
        status = data.get("status", "new")
        status_scores = {
            "new": 15.0,
            "monitoring": 12.0,
            "alert_sent": 8.0,
            "archived": 3.0,
            "blacklisted": 0.0,
        }
        return status_scores.get(status, 5.0)
