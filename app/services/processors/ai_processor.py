"""
AI Analysis Processor - Orchestrates AI-powered analysis of crypto projects.
Gathers all available data, sends to AI models, parses results,
and persists to AIReport table. Updates Engine 5 scores.
"""

import json
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.analysis import AIReport, RedFlag
from app.models.onchain import OnchainData
from app.models.project import Project, ProjectScore
from app.models.timeseries import MarketData, SocialData
from app.services.ai.prompts import (
    QUICK_SCAN_SYSTEM,
    SYSTEM_PROMPT,
    build_analysis_prompt,
    build_quick_scan_prompt,
)
from app.services.ai.providers import BaseAIProvider, get_available_providers

logger = structlog.get_logger()

MIN_SCORE_FOR_FULL_ANALYSIS = 30.0
MAX_PROJECTS_PER_RUN = 20
MAX_QUICK_SCAN_PER_RUN = 50


class AIAnalysisProcessor:
    """Orchestrates AI analysis across multiple providers."""

    def __init__(self):
        self._providers: list[BaseAIProvider] | None = None

    def _get_providers(self) -> list[BaseAIProvider]:
        if self._providers is None:
            self._providers = get_available_providers()
        return self._providers

    async def close_all(self) -> None:
        if self._providers:
            for provider in self._providers:
                await provider.close()

    async def run_analysis_cycle(self, db: AsyncSession) -> dict:
        """Run a full AI analysis cycle:
        1. Quick-scan new/unanalyzed projects
        2. Full analysis on top-scoring projects
        3. Re-analyze projects with significant score changes

        Returns:
            Summary dict with counts.
        """
        providers = self._get_providers()
        if not providers:
            logger.warning("ai.no_providers_configured")
            return {"quick_scans": 0, "full_analyses": 0, "skipped": True}

        quick_count = await self._quick_scan_new_projects(db, providers[0])
        full_count = await self._full_analyze_top_projects(db, providers)
        re_count = await self._re_analyze_changed_projects(db, providers)

        logger.info(
            "ai.cycle_complete",
            quick_scans=quick_count,
            full_analyses=full_count,
            re_analyses=re_count,
        )

        return {
            "quick_scans": quick_count,
            "full_analyses": full_count,
            "re_analyses": re_count,
            "skipped": False,
        }

    async def analyze_single_project(
        self, db: AsyncSession, project_id: str, report_type: str = "full"
    ) -> dict | None:
        """Analyze a single project by ID."""
        providers = self._get_providers()
        if not providers:
            logger.warning("ai.no_providers_configured")
            return None

        result = await db.execute(
            select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.red_flags))
        )
        project = result.scalar_one_or_none()
        if not project:
            logger.warning("ai.project_not_found", project_id=project_id)
            return None

        project_data = await self._gather_project_data(db, project)

        if report_type == "quick":
            return await self._do_quick_scan(db, project, project_data, providers[0])
        return await self._do_full_analysis(db, project, project_data, providers)

    async def _quick_scan_new_projects(
        self, db: AsyncSession, provider: BaseAIProvider
    ) -> int:
        """Quick scan projects that haven't been analyzed yet."""
        scanned = 0
        try:
            analyzed_ids_q = select(AIReport.project_id).distinct()
            result = await db.execute(
                select(Project)
                .where(
                    Project.is_active.is_(True),
                    Project.id.notin_(analyzed_ids_q),
                )
                .limit(MAX_QUICK_SCAN_PER_RUN)
            )
            projects = result.scalars().all()
            logger.info("ai.quick_scan_start", count=len(projects))

            for project in projects:
                try:
                    project_data = await self._gather_project_data(db, project)
                    result_data = await self._do_quick_scan(
                        db, project, project_data, provider
                    )
                    if result_data:
                        scanned += 1
                except Exception as e:
                    logger.error(
                        "ai.quick_scan_project_failed",
                        project_id=str(project.id),
                        error=str(e),
                    )

        except Exception as e:
            logger.error("ai.quick_scan_failed", error=str(e))

        return scanned

    async def _full_analyze_top_projects(
        self, db: AsyncSession, providers: list[BaseAIProvider]
    ) -> int:
        """Full analysis on top-scoring projects without recent full reports."""
        analyzed = 0
        try:
            result = await db.execute(
                select(Project)
                .join(ProjectScore)
                .where(
                    Project.is_active.is_(True),
                    ProjectScore.total_score >= MIN_SCORE_FOR_FULL_ANALYSIS,
                )
                .options(selectinload(Project.red_flags))
                .order_by(ProjectScore.total_score.desc())
                .limit(MAX_PROJECTS_PER_RUN)
            )
            projects = result.scalars().unique().all()
            logger.info("ai.full_analysis_start", count=len(projects))

            for project in projects:
                try:
                    has_recent = await self._has_recent_full_report(db, project.id)
                    if has_recent:
                        continue

                    project_data = await self._gather_project_data(db, project)
                    result_data = await self._do_full_analysis(
                        db, project, project_data, providers
                    )
                    if result_data:
                        analyzed += 1
                except Exception as e:
                    logger.error(
                        "ai.full_analysis_project_failed",
                        project_id=str(project.id),
                        error=str(e),
                    )

        except Exception as e:
            logger.error("ai.full_analysis_failed", error=str(e))

        return analyzed

    async def _re_analyze_changed_projects(
        self, db: AsyncSession, providers: list[BaseAIProvider]
    ) -> int:
        """Re-analyze projects with significant score changes."""
        analyzed = 0
        try:
            result = await db.execute(
                select(Project)
                .join(ProjectScore)
                .where(
                    Project.is_active.is_(True),
                )
                .options(selectinload(Project.red_flags))
                .order_by(ProjectScore.created_at.desc())
                .limit(100)
            )
            projects = result.scalars().unique().all()

            for project in projects:
                try:
                    needs_reanalysis = await self._score_changed_significantly(
                        db, project.id
                    )
                    if not needs_reanalysis:
                        continue

                    project_data = await self._gather_project_data(db, project)
                    result_data = await self._do_full_analysis(
                        db, project, project_data, providers
                    )
                    if result_data:
                        analyzed += 1

                    if analyzed >= 5:
                        break

                except Exception as e:
                    logger.error(
                        "ai.reanalysis_project_failed",
                        project_id=str(project.id),
                        error=str(e),
                    )

        except Exception as e:
            logger.error("ai.reanalysis_failed", error=str(e))

        return analyzed

    async def _do_quick_scan(
        self,
        db: AsyncSession,
        project: Project,
        project_data: dict,
        provider: BaseAIProvider,
    ) -> dict | None:
        """Execute a quick scan on a single project."""
        prompt = build_quick_scan_prompt(project_data)
        messages = [
            {"role": "system", "content": QUICK_SCAN_SYSTEM},
            {"role": "user", "content": prompt},
        ]

        response = await provider.chat(
            messages=messages,
            temperature=0.2,
            max_tokens=512,
            response_format={"type": "json_object"},
        )

        if not response:
            return None

        structured = response.structured_data or {}
        ai_score = structured.get("score", 0)

        report = AIReport(
            project_id=project.id,
            report_type="quick_scan",
            ai_model=response.model,
            summary=structured.get("verdict", response.content[:500]),
            full_report=response.content,
            recommendation=structured.get("risk", "unknown"),
            ai_score=ai_score,
            confidence=0.5,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            cost_usd=response.cost_usd,
            structured_data=structured,
        )
        db.add(report)

        logger.info(
            "ai.quick_scan_done",
            project=project.name,
            score=ai_score,
            provider=provider.provider_name,
        )

        return structured

    async def _do_full_analysis(
        self,
        db: AsyncSession,
        project: Project,
        project_data: dict,
        providers: list[BaseAIProvider],
    ) -> dict | None:
        """Execute full analysis, trying multiple providers for consensus."""
        prompt = build_analysis_prompt(project_data)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        best_result = None
        all_scores: list[float] = []

        for provider in providers[:2]:
            response = await provider.chat(
                messages=messages,
                temperature=0.3,
                max_tokens=4096,
                response_format={"type": "json_object"},
            )

            if not response:
                continue

            structured = response.structured_data
            if not structured:
                try:
                    structured = json.loads(response.content)
                except json.JSONDecodeError:
                    structured = {"raw_response": response.content}

            ai_score = structured.get("overall_score", 0)
            confidence = structured.get("confidence", 0.5)
            all_scores.append(ai_score)

            ai_red_flags = structured.get("red_flags", [])
            for flag_data in ai_red_flags:
                severity = flag_data.get("severity", "medium")
                flag_type = flag_data.get("type", "ai_detected")
                description = flag_data.get("description", "")

                existing = await db.execute(
                    select(RedFlag).where(
                        RedFlag.project_id == project.id,
                        RedFlag.flag_type == flag_type,
                        RedFlag.detected_by == f"ai_{provider.provider_name}",
                        RedFlag.is_active.is_(True),
                    )
                )
                if not existing.scalar_one_or_none():
                    red_flag = RedFlag(
                        project_id=project.id,
                        flag_type=flag_type,
                        severity=severity,
                        title=f"AI: {description[:200]}",
                        description=description,
                        detected_by=f"ai_{provider.provider_name}",
                        engine="engine5",
                        confidence=confidence,
                        evidence={"source": provider.provider_name, "model": response.model},
                    )
                    db.add(red_flag)

            report = AIReport(
                project_id=project.id,
                report_type="full_analysis",
                ai_model=response.model,
                summary=structured.get("summary", response.content[:500]),
                full_report=response.content,
                recommendation=structured.get("recommendation", "HOLD"),
                ai_score=ai_score,
                confidence=confidence,
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                cost_usd=response.cost_usd,
                structured_data=structured,
            )
            db.add(report)

            if best_result is None or confidence > best_result.get("confidence", 0):
                best_result = {
                    "overall_score": ai_score,
                    "confidence": confidence,
                    "recommendation": structured.get("recommendation", "HOLD"),
                    "summary": structured.get("summary", ""),
                    "risk_level": structured.get("risk_level", "medium"),
                    "analysis": structured.get("analysis", {}),
                    "red_flags": ai_red_flags,
                    "provider": provider.provider_name,
                    "model": response.model,
                }

        if all_scores and len(all_scores) >= 2:
            consensus_score = sum(all_scores) / len(all_scores)
            if best_result:
                best_result["consensus_score"] = consensus_score
                best_result["score_variance"] = max(all_scores) - min(all_scores)

        if best_result:
            logger.info(
                "ai.full_analysis_done",
                project=project.name,
                score=best_result.get("overall_score"),
                recommendation=best_result.get("recommendation"),
                providers_used=len(all_scores),
            )

        return best_result

    async def _gather_project_data(
        self, db: AsyncSession, project: Project
    ) -> dict:
        """Gather all available data for a project into a single dict."""
        data: dict = {
            "name": project.name,
            "symbol": project.symbol,
            "contract_address": project.contract_address,
            "blockchain": project.blockchain,
            "website": project.website,
            "description": project.description,
            "category": project.category,
            "source": project.source,
            "status": project.status,
            "twitter_url": project.twitter_url,
            "telegram_url": project.telegram_url,
            "discord_url": project.discord_url,
            "github_url": project.github_url,
        }

        market_result = await db.execute(
            select(MarketData)
            .where(MarketData.project_id == project.id)
            .order_by(MarketData.time.desc())
            .limit(1)
        )
        market_row = market_result.scalar_one_or_none()
        if market_row:
            data["market_data"] = {
                "price_usd": market_row.price_usd,
                "volume_24h": market_row.volume_24h,
                "market_cap": market_row.market_cap,
                "fdv": market_row.fdv,
                "liquidity_usd": market_row.liquidity_usd,
                "price_change_1h": market_row.price_change_1h,
                "price_change_24h": market_row.price_change_24h,
                "price_change_7d": market_row.price_change_7d,
                "buy_count": market_row.buy_count,
                "sell_count": market_row.sell_count,
                "holders_count": market_row.holders_count,
            }

        social_result = await db.execute(
            select(SocialData)
            .where(SocialData.project_id == project.id)
            .order_by(SocialData.time.desc())
            .limit(1)
        )
        social_row = social_result.scalar_one_or_none()
        if social_row:
            data["social_data"] = {
                "twitter_followers": social_row.twitter_followers,
                "twitter_engagement_rate": social_row.twitter_engagement_rate,
                "telegram_members": social_row.telegram_members,
                "telegram_online": social_row.telegram_online,
                "reddit_subscribers": social_row.reddit_subscribers,
                "reddit_active_users": social_row.reddit_active_users,
                "sentiment_label": social_row.sentiment_label,
            }

        onchain_result = await db.execute(
            select(OnchainData)
            .where(OnchainData.project_id == project.id)
            .order_by(OnchainData.created_at.desc())
            .limit(1)
        )
        onchain_row = onchain_result.scalar_one_or_none()
        if onchain_row:
            data["onchain_data"] = {
                "is_verified": onchain_row.is_verified,
                "is_renounced": onchain_row.is_renounced,
                "has_proxy": onchain_row.has_proxy,
                "has_mint_function": onchain_row.has_mint_function,
                "has_blacklist": onchain_row.has_blacklist,
                "buy_tax": onchain_row.buy_tax,
                "sell_tax": onchain_row.sell_tax,
                "holder_count": onchain_row.holder_count,
                "top10_holder_pct": onchain_row.top10_holder_pct,
                "liquidity_locked": onchain_row.liquidity_locked,
            }

        score_result = await db.execute(
            select(ProjectScore)
            .where(ProjectScore.project_id == project.id)
            .order_by(ProjectScore.created_at.desc())
            .limit(1)
        )
        score_row = score_result.scalar_one_or_none()
        if score_row:
            data["engine_scores"] = {
                "engine1": score_row.engine1_score,
                "engine2": score_row.engine2_score,
                "engine3": score_row.engine3_score,
                "engine4": score_row.engine4_score,
                "total": score_row.total_score,
            }

        red_flags = project.red_flags or []
        data["red_flags"] = [
            {
                "flag_type": f.flag_type,
                "severity": f.severity,
                "title": f.title,
            }
            for f in red_flags
            if f.is_active
        ]

        return data

    async def _has_recent_full_report(
        self, db: AsyncSession, project_id, hours: int = 6
    ) -> bool:
        """Check if a full analysis report was created in the last N hours."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        result = await db.execute(
            select(AIReport.id)
            .where(
                AIReport.project_id == project_id,
                AIReport.report_type == "full_analysis",
                AIReport.created_at >= cutoff,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def _score_changed_significantly(
        self, db: AsyncSession, project_id, threshold: float = 15.0
    ) -> bool:
        """Check if the project's score changed by more than threshold."""
        result = await db.execute(
            select(ProjectScore.total_score)
            .where(ProjectScore.project_id == project_id)
            .order_by(ProjectScore.created_at.desc())
            .limit(2)
        )
        scores = result.scalars().all()
        if len(scores) < 2:
            return False
        return abs(scores[0] - scores[1]) >= threshold
