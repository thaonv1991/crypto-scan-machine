"""
Twitter/X Collector - Engine 3 (Social Intelligence)
*** REQUIRES API KEY ***
Free tier is very limited. Consider using:
- Twitter API v2 Basic ($100/mo): 10k tweets/read per month
- Twitter API v2 Free: Only post tweets, very limited read

Alternative free approach: Use Nitter instances or scraping (unreliable).

For now, this collector is a placeholder that will work once API keys are provided.
Set TWITTER_BEARER_TOKEN in .env to enable.
"""

import structlog

from app.services.collectors.base import BaseCollector

logger = structlog.get_logger()

BASE_URL = "https://api.twitter.com/2"


class TwitterCollector(BaseCollector):
    """Collect social data from Twitter/X API.

    REQUIRES: Twitter API Bearer Token.
    Get API access at https://developer.twitter.com/en/portal/dashboard

    Pricing:
    - Free tier: Write-only, 1 app, 1500 tweets/month
    - Basic ($100/mo): Read 10k tweets/month, 50 requests/15min
    - Pro ($5000/mo): Full access
    """

    source_name = "twitter"
    rate_limit_name = "twitter"

    def __init__(self, bearer_token: str = ""):
        super().__init__()
        self._bearer_token = bearer_token

    def is_configured(self) -> bool:
        return bool(self._bearer_token)

    async def fetch(self, url: str, params: dict | None = None) -> dict:
        """Override fetch to add Twitter auth header."""
        if not self.is_configured():
            raise RuntimeError("Twitter API not configured. Set bearer token.")

        from app.utils.rate_limiter import rate_limiters

        await rate_limiters.wait_and_acquire(self.rate_limit_name)
        client = await self.get_client()
        response = await client.get(
            url,
            params=params,
            headers={"Authorization": f"Bearer {self._bearer_token}"},
        )
        response.raise_for_status()
        return response.json()

    async def get_user_by_username(self, username: str) -> dict | None:
        """Get Twitter user info by username."""
        if not self.is_configured():
            logger.warning("twitter.not_configured")
            return None

        url = f"{BASE_URL}/users/by/username/{username}"
        params = {
            "user.fields": "public_metrics,description,profile_image_url,created_at,verified",
        }
        try:
            data = await self.fetch(url, params=params)
            return data.get("data")
        except Exception as e:
            logger.error("twitter.user_lookup_failed", username=username, error=str(e))
            return None

    async def get_user_tweets(self, user_id: str, max_results: int = 10) -> list[dict]:
        """Get recent tweets from a user."""
        if not self.is_configured():
            return []

        url = f"{BASE_URL}/users/{user_id}/tweets"
        params = {
            "max_results": str(max_results),
            "tweet.fields": "public_metrics,created_at",
        }
        try:
            data = await self.fetch(url, params=params)
            return data.get("data", [])
        except Exception as e:
            logger.error("twitter.user_tweets_failed", user_id=user_id, error=str(e))
            return []

    async def collect(self, **kwargs) -> list[dict]:
        """Collect Twitter social data."""
        if not self.is_configured():
            logger.warning("twitter.skipped", reason="Bearer token not configured")
            return []

        username = kwargs.get("username", "")
        if not username:
            return []

        user = await self.get_user_by_username(username)
        if not user:
            return []

        return [user]

    def normalize_to_social_data(self, user: dict) -> dict:
        """Normalize Twitter user data to our SocialData format."""
        metrics = user.get("public_metrics", {})
        followers = metrics.get("followers_count", 0)
        following = metrics.get("following_count", 0)
        tweet_count = metrics.get("tweet_count", 0)

        engagement_rate = 0.0
        if followers > 0 and tweet_count > 0:
            listed = metrics.get("listed_count", 0)
            engagement_rate = (listed / followers) * 100 if followers else 0.0

        return {
            "twitter_followers": followers,
            "twitter_following": following,
            "twitter_tweets_count": tweet_count,
            "twitter_engagement_rate": engagement_rate,
            "source": "twitter",
            "extra_data": {
                "twitter_id": user.get("id"),
                "username": user.get("username"),
                "description": user.get("description"),
                "verified": user.get("verified"),
                "created_at": user.get("created_at"),
                "profile_image_url": user.get("profile_image_url"),
            },
        }
