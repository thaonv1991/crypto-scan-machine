"""
Scoring Processor - Orchestrates score calculation across all 5 engines.
Queries latest data for each project, runs scorers, and persists results
to ProjectScore and ScoreHistory tables.
"""

from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.onchain import OnchainData
from app.models.project import Project, ProjectScore
from app.models.timeseries import MarketData, ScoreHistory, SocialData
from app.services.scorers.ai_scorer import AIScorer
from app.services.scorers.discovery_scorer import DiscoveryScorer
from app.services.scorers.market_scorer import MarketScorer
from app.services.scorers.security_scorer import SecurityScorer
from app.services.scorers.social_scorer import SocialScorer

logger = structlog.get_logger()

DEFAULT_WEIGHTS = {
    "engine1": 0.15,
    "engine2": 0.30,
    "engine3": 0.15,
    "engine4": 0.25,
    "engine5": 0.15,
}


class ScoringProcessor:
    """Orchestrates score calculation for all active projects."""

    def __init__(self, weights: dict[str, float] | None = None):
        self.weights = weights or DEFAULT_WEIGHTS
        self.discovery_scorer = DiscoveryScorer()
        self.market_scorer = MarketScorer()
        self.social_scorer = SocialScorer()
        self.security_scorer = SecurityScorer()
        self.ai_scorer = AIScorer()

    async def calculate_all_scores(self, db: AsyncSession) -> int:
        """Calculate scores for all active projects.

        Returns:
            Number of projects scored.
        """
        scored_count = 0
        try:
            result = await db.execute(
                select(Project)
                .where(Project.is_active.is_(True))
                .options(selectinload(Project.red_flags))
            )
            projects = result.scalars().all()
            logger.info("scoring.start", project_count=len(projects))

            for project in projects:
                try:
                    score_result = await self._score_project(db, project)
                    if score_result:
                        scored_count += 1
                except Exception as e:
                    logger.error(
                        "scoring.project_failed",
                        project_id=str(project.id),
                        error=str(e),
                    )

            if scored_count > 0:
                await db.flush()

            logger.info("scoring.complete", scored=scored_count, total=len(projects))

        except Exception as e:
            logger.error("scoring.failed", error=str(e))

        return scored_count

    async def calculate_project_score(self, db: AsyncSession, project_id: str) -> dict | None:
        """Calculate score for a single project by ID.

        Returns:
            Score result dict or None if project not found.
        """
        try:
            result = await db.execute(
                select(Project)
                .where(Project.id == project_id)
                .options(selectinload(Project.red_flags))
            )
            project = result.scalar_one_or_none()

            if not project:
                logger.warning("scoring.project_not_found", project_id=project_id)
                return None

            score_result = await self._score_project(db, project)
            if score_result:
                await db.flush()
            return score_result

        except Exception as e:
            logger.error("scoring.single_failed", project_id=project_id, error=str(e))
            return None

    async def _score_project(self, db: AsyncSession, project: Project) -> dict | None:
        """Run all 5 scoring engines for a single project."""
        discovery_data = self._build_discovery_data(project)
        market_data = await self._get_latest_market_data(db, project.id)
        social_data = await self._get_latest_social_data(db, project.id)
        security_data = await self._get_latest_security_data(db, project)

        e1 = self.discovery_scorer.calculate(discovery_data)
        e2 = self.market_scorer.calculate(market_data)
        e3 = self.social_scorer.calculate(social_data)
        e4 = self.security_scorer.calculate(security_data)
        e5 = self.ai_scorer.calculate({})

        total_score = (
            e1["score"] * self.weights["engine1"]
            + e2["score"] * self.weights["engine2"]
            + e3["score"] * self.weights["engine3"]
            + e4["score"] * self.weights["engine4"]
            + e5["score"] * self.weights["engine5"]
        )

        red_flags = [f for f in (project.red_flags or []) if f.is_active]
        has_critical = any(f.severity == "critical" for f in red_flags)

        score_breakdown = {
            "engine1_discovery": e1["breakdown"],
            "engine2_market": e2["breakdown"],
            "engine3_social": e3["breakdown"],
            "engine4_security": e4["breakdown"],
            "engine5_ai": e5["breakdown"],
            "weights": self.weights,
        }

        project_score = ProjectScore(
            project_id=project.id,
            engine1_score=e1["score"],
            engine2_score=e2["score"],
            engine3_score=e3["score"],
            engine4_score=e4["score"],
            engine5_score=e5["score"],
            total_score=round(total_score, 2),
            weights=self.weights,
            score_breakdown=score_breakdown,
            red_flag_count=len(red_flags),
            has_critical_flag=has_critical,
        )
        db.add(project_score)

        previous_score = await self._get_previous_total_score(db, project.id)
        score_delta = round(total_score - previous_score, 2) if previous_score is not None else None

        score_history = ScoreHistory(
            time=datetime.now(timezone.utc),
            project_id=project.id,
            engine1_score=e1["score"],
            engine2_score=e2["score"],
            engine3_score=e3["score"],
            engine4_score=e4["score"],
            engine5_score=e5["score"],
            total_score=round(total_score, 2),
            score_delta=score_delta,
            red_flag_count=len(red_flags),
        )
        db.add(score_history)

        logger.info(
            "scoring.project_scored",
            project_id=str(project.id),
            project_name=project.name,
            total=round(total_score, 2),
            e1=e1["score"],
            e2=e2["score"],
            e3=e3["score"],
            e4=e4["score"],
            e5=e5["score"],
            flags=len(red_flags),
        )

        return {
            "project_id": str(project.id),
            "total_score": round(total_score, 2),
            "engine1_score": e1["score"],
            "engine2_score": e2["score"],
            "engine3_score": e3["score"],
            "engine4_score": e4["score"],
            "engine5_score": e5["score"],
            "red_flag_count": len(red_flags),
            "has_critical_flag": has_critical,
            "score_delta": score_delta,
            "breakdown": score_breakdown,
        }

    def _build_discovery_data(self, project: Project) -> dict:
        """Build input data dict for the discovery scorer."""
        return {
            "name": project.name,
            "symbol": project.symbol,
            "contract_address": project.contract_address,
            "blockchain": project.blockchain,
            "website": project.website,
            "description": project.description,
            "logo_url": project.logo_url,
            "category": project.category,
            "twitter_url": project.twitter_url,
            "telegram_url": project.telegram_url,
            "discord_url": project.discord_url,
            "github_url": project.github_url,
            "source": project.source,
            "sources": [project.source],
            "discovered_at": project.discovered_at,
            "status": project.status,
        }

    async def _get_latest_market_data(self, db: AsyncSession, project_id) -> dict:
        """Fetch the most recent market data for a project."""
        result = await db.execute(
            select(MarketData)
            .where(MarketData.project_id == project_id)
            .order_by(MarketData.time.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if not row:
            return {}

        return {
            "price_usd": row.price_usd,
            "price_btc": row.price_btc,
            "price_eth": row.price_eth,
            "volume_24h": row.volume_24h,
            "volume_change_pct": row.volume_change_pct,
            "market_cap": row.market_cap,
            "fdv": row.fdv,
            "liquidity_usd": row.liquidity_usd,
            "liquidity_score": row.liquidity_score,
            "price_change_1h": row.price_change_1h,
            "price_change_24h": row.price_change_24h,
            "price_change_7d": row.price_change_7d,
            "buy_count": row.buy_count,
            "sell_count": row.sell_count,
            "holders_count": row.holders_count,
        }

    async def _get_latest_social_data(self, db: AsyncSession, project_id) -> dict:
        """Fetch the most recent social data for a project."""
        result = await db.execute(
            select(SocialData)
            .where(SocialData.project_id == project_id)
            .order_by(SocialData.time.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if not row:
            return {}

        return {
            "twitter_followers": row.twitter_followers,
            "twitter_following": row.twitter_following,
            "twitter_tweets_count": row.twitter_tweets_count,
            "twitter_engagement_rate": row.twitter_engagement_rate,
            "twitter_mentions_count": row.twitter_mentions_count,
            "telegram_members": row.telegram_members,
            "telegram_online": row.telegram_online,
            "telegram_messages_24h": row.telegram_messages_24h,
            "reddit_subscribers": row.reddit_subscribers,
            "reddit_active_users": row.reddit_active_users,
            "reddit_posts_24h": row.reddit_posts_24h,
            "sentiment_score": row.sentiment_score,
            "sentiment_label": row.sentiment_label,
        }

    async def _get_latest_security_data(self, db: AsyncSession, project: Project) -> dict:
        """Fetch the most recent on-chain/security data for a project."""
        result = await db.execute(
            select(OnchainData)
            .where(OnchainData.project_id == project.id)
            .order_by(OnchainData.created_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()

        data: dict = {}
        if row:
            data = {
                "holder_count": row.holder_count,
                "top10_holder_pct": row.top10_holder_pct,
                "top50_holder_pct": row.top50_holder_pct,
                "is_verified": row.is_verified,
                "is_renounced": row.is_renounced,
                "has_proxy": row.has_proxy,
                "has_mint_function": row.has_mint_function,
                "has_blacklist": row.has_blacklist,
                "buy_tax": row.buy_tax,
                "sell_tax": row.sell_tax,
                "liquidity_locked": row.liquidity_locked,
            }

        active_flags = [f for f in (project.red_flags or []) if f.is_active]
        data["red_flags"] = [
            {
                "flag_type": f.flag_type,
                "severity": f.severity,
                "is_active": f.is_active,
            }
            for f in active_flags
        ]

        return data

    async def _get_previous_total_score(self, db: AsyncSession, project_id) -> float | None:
        """Get the previous total score for delta calculation."""
        result = await db.execute(
            select(ProjectScore.total_score)
            .where(ProjectScore.project_id == project_id)
            .order_by(ProjectScore.created_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return row
