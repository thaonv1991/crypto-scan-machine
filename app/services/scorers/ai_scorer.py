"""Engine 5: AI Score (Stub for Phase 3).

Will integrate with DeepSeek/Gemini/GPT-4o-mini for comprehensive AI analysis.
Currently returns a neutral score with no breakdown.
"""

import structlog

from app.services.scorers.base import BaseScorer

logger = structlog.get_logger()


class AIScorer(BaseScorer):
    """Stub scorer for AI-powered analysis.

    Will be fully implemented in Phase 3. Currently returns 0 to indicate
    that AI analysis has not been performed.
    """

    engine_name = "engine5_ai"

    def calculate(self, data: dict) -> dict:
        ai_score = data.get("ai_score")
        if ai_score is not None:
            return {
                "score": self.clamp(ai_score),
                "breakdown": {
                    "source": data.get("ai_model", "unknown"),
                    "confidence": data.get("confidence", 0.0),
                },
            }

        return {
            "score": 0.0,
            "breakdown": {
                "status": "not_implemented",
                "note": "AI analysis will be available in Phase 3",
            },
        }
