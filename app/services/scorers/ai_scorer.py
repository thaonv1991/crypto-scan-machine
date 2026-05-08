"""Engine 5: AI Score.

Uses the latest AI analysis report (from DeepSeek/Gemini/GPT-4o-mini)
to produce Engine 5 score. Falls back to 0 if no AI report is available.
"""

import structlog

from app.services.scorers.base import BaseScorer

logger = structlog.get_logger()


class AIScorer(BaseScorer):
    """Scorer powered by AI analysis reports.

    Uses the latest AIReport for the project to derive a score.
    If multiple reports exist, uses the one with highest confidence.
    Falls back to 0 if no AI analysis has been performed.
    """

    engine_name = "engine5_ai"

    def calculate(self, data: dict) -> dict:
        ai_score = data.get("ai_score")
        if ai_score is not None:
            confidence = data.get("confidence", 0.5)
            recommendation = data.get("recommendation", "HOLD")
            risk_level = data.get("risk_level", "medium")

            rec_bonus = {
                "STRONG_BUY": 10,
                "BUY": 5,
                "HOLD": 0,
                "AVOID": -10,
                "STRONG_AVOID": -20,
            }.get(recommendation, 0)

            adjusted = ai_score * confidence + rec_bonus
            final_score = self.clamp(adjusted)

            analysis = data.get("analysis", {})
            sub_scores = {}
            for category in ("tokenomics", "market_health", "security", "community", "potential"):
                cat_data = analysis.get(category, {})
                if isinstance(cat_data, dict) and "score" in cat_data:
                    sub_scores[category] = cat_data["score"]

            return {
                "score": round(final_score, 2),
                "breakdown": {
                    "raw_ai_score": ai_score,
                    "confidence": confidence,
                    "recommendation": recommendation,
                    "risk_level": risk_level,
                    "recommendation_adjustment": rec_bonus,
                    "model": data.get("ai_model", "unknown"),
                    "provider": data.get("provider", "unknown"),
                    "sub_scores": sub_scores,
                },
            }

        return {
            "score": 0.0,
            "breakdown": {
                "status": "no_ai_report",
                "note": "No AI analysis available yet. Configure DEEPSEEK_API_KEY, GEMINI_API_KEY, or OPENAI_API_KEY.",
            },
        }
