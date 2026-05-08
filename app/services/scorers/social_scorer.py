"""Engine 3: Social Score.

Evaluates social media presence and community engagement.
Higher scores indicate active, growing communities with genuine engagement.
"""

import structlog

from app.services.scorers.base import BaseScorer

logger = structlog.get_logger()


class SocialScorer(BaseScorer):
    """Scores based on social media metrics.

    Sub-scores:
    - twitter (0-30): Twitter presence and engagement
    - telegram (0-25): Telegram community size and activity
    - reddit (0-25): Reddit community engagement
    - sentiment (0-20): Overall sentiment analysis
    """

    engine_name = "engine3_social"

    def calculate(self, data: dict) -> dict:
        try:
            twitter_score = self._score_twitter(data)
            telegram_score = self._score_telegram(data)
            reddit_score = self._score_reddit(data)
            sentiment_score = self._score_sentiment(data)

            total = self.clamp(
                twitter_score + telegram_score + reddit_score + sentiment_score
            )

            return {
                "score": round(total, 2),
                "breakdown": {
                    "twitter": round(twitter_score, 2),
                    "telegram": round(telegram_score, 2),
                    "reddit": round(reddit_score, 2),
                    "sentiment": round(sentiment_score, 2),
                },
            }
        except Exception as e:
            logger.error("scorer.social_failed", error=str(e))
            return {"score": 0.0, "breakdown": {}}

    def _score_twitter(self, data: dict) -> float:
        """Score based on Twitter metrics."""
        followers = data.get("twitter_followers", 0) or 0
        engagement = data.get("twitter_engagement_rate", 0) or 0
        mentions = data.get("twitter_mentions_count", 0) or 0
        has_url = bool(data.get("twitter_url"))

        if not has_url and followers == 0:
            return 0.0

        score = 2.0 if has_url else 0.0

        if followers >= 100_000:
            score += 12.0
        elif followers >= 50_000:
            score += 10.0
        elif followers >= 10_000:
            score += 8.0
        elif followers >= 5_000:
            score += 6.0
        elif followers >= 1_000:
            score += 4.0
        elif followers > 0:
            score += 2.0

        if engagement >= 5.0:
            score += 8.0
        elif engagement >= 3.0:
            score += 6.0
        elif engagement >= 1.0:
            score += 4.0
        elif engagement > 0:
            score += 2.0

        if mentions >= 100:
            score += 8.0
        elif mentions >= 50:
            score += 5.0
        elif mentions >= 10:
            score += 3.0
        elif mentions > 0:
            score += 1.0

        return min(30.0, score)

    def _score_telegram(self, data: dict) -> float:
        """Score based on Telegram metrics."""
        members = data.get("telegram_members", 0) or 0
        online = data.get("telegram_online", 0) or 0
        messages = data.get("telegram_messages_24h", 0) or 0
        has_url = bool(data.get("telegram_url"))

        if not has_url and members == 0:
            return 0.0

        score = 2.0 if has_url else 0.0

        if members >= 50_000:
            score += 8.0
        elif members >= 10_000:
            score += 6.0
        elif members >= 5_000:
            score += 5.0
        elif members >= 1_000:
            score += 3.0
        elif members > 0:
            score += 1.0

        if members > 0 and online > 0:
            active_ratio = online / members
            if active_ratio >= 0.1:
                score += 5.0
            elif active_ratio >= 0.05:
                score += 3.0
            elif active_ratio >= 0.02:
                score += 2.0

        if messages >= 500:
            score += 5.0
        elif messages >= 100:
            score += 3.0
        elif messages >= 10:
            score += 2.0
        elif messages > 0:
            score += 1.0

        return min(25.0, score)

    def _score_reddit(self, data: dict) -> float:
        """Score based on Reddit metrics."""
        subscribers = data.get("reddit_subscribers", 0) or 0
        active = data.get("reddit_active_users", 0) or 0
        posts = data.get("reddit_posts_24h", 0) or 0

        if subscribers == 0 and active == 0:
            return 0.0

        score = 0.0

        if subscribers >= 100_000:
            score += 10.0
        elif subscribers >= 50_000:
            score += 8.0
        elif subscribers >= 10_000:
            score += 6.0
        elif subscribers >= 1_000:
            score += 4.0
        elif subscribers > 0:
            score += 2.0

        if subscribers > 0 and active > 0:
            active_ratio = active / subscribers
            if active_ratio >= 0.05:
                score += 5.0
            elif active_ratio >= 0.02:
                score += 3.0
            elif active_ratio >= 0.01:
                score += 2.0

        if posts >= 50:
            score += 5.0
        elif posts >= 20:
            score += 3.0
        elif posts >= 5:
            score += 2.0
        elif posts > 0:
            score += 1.0

        return min(25.0, score)

    def _score_sentiment(self, data: dict) -> float:
        """Score based on sentiment analysis."""
        sentiment_score = data.get("sentiment_score")
        sentiment_label = data.get("sentiment_label", "")

        if sentiment_score is not None:
            normalized = (sentiment_score + 1) / 2 * 20
            return min(20.0, max(0.0, normalized))

        label_scores = {
            "very_positive": 18.0,
            "positive": 14.0,
            "neutral": 10.0,
            "negative": 4.0,
            "very_negative": 1.0,
        }
        return label_scores.get(sentiment_label, 10.0)
