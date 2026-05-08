"""
Reddit Collector - Engine 3 (Social Intelligence)
Uses Reddit's public JSON API (no auth needed for read-only public data).
Append .json to any Reddit URL to get JSON data.

Rate limit: ~10 req/min for unauthenticated access.

For authenticated access (higher limits):
- Create an app at https://www.reddit.com/prefs/apps
- Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in .env
"""

import structlog

from app.services.collectors.base import BaseCollector

logger = structlog.get_logger()

BASE_URL = "https://www.reddit.com"


class RedditCollector(BaseCollector):
    """Collect social data from Reddit public API (no auth needed for basic data)."""

    source_name = "reddit"
    rate_limit_name = "reddit"

    async def get_subreddit_about(self, subreddit: str) -> dict | None:
        """Get subreddit info (subscribers, active users, etc.)."""
        url = f"{BASE_URL}/r/{subreddit}/about.json"
        try:
            data = await self.fetch(url)
            return data.get("data")
        except Exception as e:
            logger.error("reddit.subreddit_about_failed", subreddit=subreddit, error=str(e))
            return None

    async def get_subreddit_posts(self, subreddit: str, sort: str = "new", limit: int = 25) -> list[dict]:
        """Get recent posts from a subreddit."""
        url = f"{BASE_URL}/r/{subreddit}/{sort}.json"
        try:
            data = await self.fetch(url, params={"limit": str(limit)})
            children = data.get("data", {}).get("children", [])
            return [c.get("data", {}) for c in children]
        except Exception as e:
            logger.error("reddit.subreddit_posts_failed", subreddit=subreddit, error=str(e))
            return []

    async def search_subreddit(self, query: str, limit: int = 10) -> list[dict]:
        """Search for subreddits by name."""
        url = f"{BASE_URL}/subreddits/search.json"
        try:
            data = await self.fetch(url, params={"q": query, "limit": str(limit)})
            children = data.get("data", {}).get("children", [])
            return [c.get("data", {}) for c in children]
        except Exception as e:
            logger.error("reddit.search_failed", query=query, error=str(e))
            return []

    async def collect(self, **kwargs) -> list[dict]:
        """Collect Reddit social data."""
        subreddit = kwargs.get("subreddit", "")
        if not subreddit:
            return []

        about = await self.get_subreddit_about(subreddit)
        if about:
            return [about]
        return []

    def normalize_to_social_data(self, subreddit: dict) -> dict:
        """Normalize Reddit subreddit data to our SocialData format."""
        return {
            "reddit_subscribers": subreddit.get("subscribers"),
            "reddit_active_users": subreddit.get("accounts_active"),
            "reddit_posts_24h": None,
            "source": "reddit",
            "extra_data": {
                "subreddit_name": subreddit.get("display_name"),
                "subreddit_id": subreddit.get("name"),
                "title": subreddit.get("title"),
                "description": subreddit.get("public_description"),
                "created_utc": subreddit.get("created_utc"),
                "over18": subreddit.get("over18"),
            },
        }
