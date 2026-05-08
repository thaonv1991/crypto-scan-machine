"""
YouTube Data API v3 Collector - Crypto social intelligence.
*** REQUIRES API KEY ***
Free tier: 10,000 units/day (1 search = 100 units)
Get API key at: https://console.cloud.google.com/apis/library/youtube.googleapis.com

Monitors crypto YouTube channels and trending videos for token mentions.
"""

import structlog

from app.core.config import settings
from app.services.collectors.base import BaseCollector

logger = structlog.get_logger()

BASE_URL = "https://www.googleapis.com/youtube/v3"


class YouTubeCollector(BaseCollector):
    """Collect crypto-related YouTube data for social intelligence."""

    source_name = "youtube"
    rate_limit_name = "youtube"

    def _get_api_key(self) -> str:
        return settings.youtube_api_key

    def is_configured(self) -> bool:
        return bool(settings.youtube_api_key)

    async def search_videos(
        self,
        query: str,
        max_results: int = 10,
        order: str = "date",
        published_after: str | None = None,
    ) -> list[dict]:
        """Search for crypto-related YouTube videos.

        Args:
            query: Search query (e.g., token name/symbol)
            max_results: Number of results (max 50, costs 100 units per request)
            order: 'date', 'relevance', 'viewCount', 'rating'
            published_after: ISO 8601 datetime (e.g., '2024-01-01T00:00:00Z')
        """
        if not self.is_configured():
            logger.warning("youtube.not_configured", hint="Set YOUTUBE_API_KEY")
            return []

        url = f"{BASE_URL}/search"
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": max_results,
            "order": order,
            "key": self._get_api_key(),
        }
        if published_after:
            params["publishedAfter"] = published_after

        try:
            data = await self.fetch(url, params=params)
            return data.get("items", [])
        except Exception as e:
            logger.error("youtube.search_failed", query=query, error=str(e))
            return []

    async def get_video_stats(self, video_ids: list[str]) -> list[dict]:
        """Get statistics (views, likes, comments) for videos.

        Costs 1 unit per request (efficient batch call).
        """
        if not self.is_configured() or not video_ids:
            return []

        url = f"{BASE_URL}/videos"
        params = {
            "part": "statistics,snippet",
            "id": ",".join(video_ids[:50]),
            "key": self._get_api_key(),
        }
        try:
            data = await self.fetch(url, params=params)
            return data.get("items", [])
        except Exception as e:
            logger.error("youtube.video_stats_failed", error=str(e))
            return []

    async def get_channel_info(self, channel_ids: list[str]) -> list[dict]:
        """Get channel info (subscriber count, video count)."""
        if not self.is_configured() or not channel_ids:
            return []

        url = f"{BASE_URL}/channels"
        params = {
            "part": "statistics,snippet",
            "id": ",".join(channel_ids[:50]),
            "key": self._get_api_key(),
        }
        try:
            data = await self.fetch(url, params=params)
            return data.get("items", [])
        except Exception as e:
            logger.error("youtube.channel_info_failed", error=str(e))
            return []

    async def collect(self, **kwargs) -> list[dict]:
        """Collect YouTube social data for a token/project."""
        if not self.is_configured():
            logger.warning("youtube.skipped", reason="API key not configured")
            return []

        query = kwargs.get("query", "")
        if not query:
            return []

        crypto_query = f"{query} crypto token"
        videos = await self.search_videos(crypto_query, max_results=kwargs.get("max_results", 10))

        if not videos:
            return []

        video_ids = [v["id"]["videoId"] for v in videos if "id" in v and "videoId" in v.get("id", {})]
        stats = await self.get_video_stats(video_ids) if video_ids else []

        stats_map = {s["id"]: s.get("statistics", {}) for s in stats}

        results = []
        for video in videos:
            video_id = video.get("id", {}).get("videoId", "")
            video_stats = stats_map.get(video_id, {})
            results.append(self.normalize_to_social_data(video, video_stats))

        return results

    def normalize_to_social_data(self, video: dict, stats: dict) -> dict:
        """Normalize YouTube video data to social data format."""
        snippet = video.get("snippet", {})
        return {
            "platform": "youtube",
            "content_type": "video",
            "content_id": video.get("id", {}).get("videoId"),
            "title": snippet.get("title"),
            "author": snippet.get("channelTitle"),
            "author_id": snippet.get("channelId"),
            "published_at": snippet.get("publishedAt"),
            "views": _safe_int(stats.get("viewCount")),
            "likes": _safe_int(stats.get("likeCount")),
            "comments": _safe_int(stats.get("commentCount")),
            "source": "youtube",
            "extra_data": {
                "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url"),
                "description": snippet.get("description", "")[:500],
                "favorite_count": _safe_int(stats.get("favoriteCount")),
            },
        }


def _safe_int(value: str | int | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
