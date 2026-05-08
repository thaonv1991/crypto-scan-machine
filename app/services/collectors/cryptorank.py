"""
CryptoRank Collector - Funding rounds, project data, and rankings.
*** REQUIRES API KEY ***
Free tier: 100 requests/day
Get API key at: https://cryptorank.io/api

Provides funding round data, VC investments, and project rankings.
"""

import structlog

from app.core.config import settings
from app.services.collectors.base import BaseCollector

logger = structlog.get_logger()

BASE_URL = "https://api.cryptorank.io/v1"


class CryptoRankCollector(BaseCollector):
    """Collect funding rounds and project rankings from CryptoRank."""

    source_name = "cryptorank"
    rate_limit_name = "cryptorank"

    def _get_api_key(self) -> str:
        return settings.cryptorank_api_key

    def is_configured(self) -> bool:
        return bool(settings.cryptorank_api_key)

    async def get_currencies(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """Get list of cryptocurrencies with basic data."""
        if not self.is_configured():
            logger.warning("cryptorank.not_configured", hint="Set CRYPTORANK_API_KEY")
            return []

        url = f"{BASE_URL}/currencies"
        try:
            data = await self.fetch(url, params={"api_key": self._get_api_key(), "limit": limit, "offset": offset})
            return data.get("data", []) if isinstance(data, dict) else []
        except Exception as e:
            logger.error("cryptorank.currencies_failed", error=str(e))
            return []

    async def get_currency_by_slug(self, slug: str) -> dict | None:
        """Get detailed data for a specific currency."""
        if not self.is_configured():
            return None

        url = f"{BASE_URL}/currencies/{slug}"
        try:
            data = await self.fetch(url, params={"api_key": self._get_api_key()})
            return data.get("data") if isinstance(data, dict) else None
        except Exception as e:
            logger.error("cryptorank.currency_detail_failed", slug=slug, error=str(e))
            return None

    async def get_funding_rounds(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """Get recent funding rounds across crypto projects."""
        if not self.is_configured():
            return []

        url = f"{BASE_URL}/funding-rounds"
        try:
            data = await self.fetch(
                url,
                params={"api_key": self._get_api_key(), "limit": limit, "offset": offset},
            )
            return data.get("data", []) if isinstance(data, dict) else []
        except Exception as e:
            logger.error("cryptorank.funding_rounds_failed", error=str(e))
            return []

    async def get_project_fundraising(self, slug: str) -> list[dict]:
        """Get fundraising details for a specific project."""
        if not self.is_configured():
            return []

        url = f"{BASE_URL}/currencies/{slug}/fundraising"
        try:
            data = await self.fetch(url, params={"api_key": self._get_api_key()})
            return data.get("data", []) if isinstance(data, dict) else []
        except Exception as e:
            logger.error("cryptorank.fundraising_failed", slug=slug, error=str(e))
            return []

    async def get_upcoming_icos(self, limit: int = 50) -> list[dict]:
        """Get upcoming ICOs/token sales."""
        if not self.is_configured():
            return []

        url = f"{BASE_URL}/icos"
        try:
            data = await self.fetch(
                url,
                params={"api_key": self._get_api_key(), "limit": limit, "status": "upcoming"},
            )
            return data.get("data", []) if isinstance(data, dict) else []
        except Exception as e:
            logger.error("cryptorank.icos_failed", error=str(e))
            return []

    async def collect(self, **kwargs) -> list[dict]:
        """Collect funding and project data from CryptoRank."""
        if not self.is_configured():
            logger.warning("cryptorank.skipped", reason="API key not configured")
            return []

        mode = kwargs.get("mode", "funding")

        if mode == "funding":
            rounds = await self.get_funding_rounds()
            return [self.normalize_funding_round(r) for r in rounds]
        elif mode == "icos":
            icos = await self.get_upcoming_icos()
            return [self.normalize_ico_to_project(i) for i in icos]
        elif mode == "detail":
            slug = kwargs.get("slug", "")
            if slug:
                data = await self.get_currency_by_slug(slug)
                return [data] if data else []
        return []

    def normalize_funding_round(self, raw: dict) -> dict:
        """Normalize CryptoRank funding round to a structured format."""
        project = raw.get("coin", {}) or {}
        return {
            "project_name": project.get("name"),
            "project_symbol": project.get("symbol"),
            "project_slug": project.get("slug"),
            "round_type": raw.get("type"),
            "amount_raised": raw.get("amount"),
            "valuation": raw.get("valuation"),
            "date": raw.get("date"),
            "investors": [inv.get("name") for inv in (raw.get("investors", []) or [])],
            "lead_investors": [inv.get("name") for inv in (raw.get("leadInvestors", []) or [])],
            "source": "cryptorank",
            "extra_data": {
                "project_rank": project.get("rank"),
                "project_category": project.get("category"),
            },
        }

    def normalize_ico_to_project(self, raw: dict) -> dict:
        """Normalize CryptoRank ICO data to project format."""
        return {
            "name": raw.get("name", ""),
            "symbol": raw.get("symbol"),
            "slug": f"cryptorank-{raw.get('slug', '')}",
            "website": raw.get("links", {}).get("web"),
            "description": raw.get("tagline") or raw.get("description"),
            "logo_url": raw.get("logo"),
            "twitter_url": raw.get("links", {}).get("twitter"),
            "telegram_url": raw.get("links", {}).get("telegram"),
            "discord_url": raw.get("links", {}).get("discord"),
            "source": "cryptorank",
            "extra_data": {
                "ico_status": raw.get("status"),
                "ico_start": raw.get("startDate"),
                "ico_end": raw.get("endDate"),
                "token_price": raw.get("price"),
                "hard_cap": raw.get("hardCap"),
                "raise_amount": raw.get("raised"),
                "platform": raw.get("platform"),
                "category": raw.get("category"),
            },
        }
