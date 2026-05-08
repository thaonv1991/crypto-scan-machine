"""
Alert Processor - Determines which projects need alerts and sends them
via Telegram. Tracks sent alerts in AlertLog to avoid duplicates.
"""

from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.analysis import AIReport, AlertLog, RedFlag
from app.models.project import Project, ProjectScore
from app.models.timeseries import ScoreHistory
from app.services.alerts.formatters import (
    format_ai_analysis_alert,
    format_daily_summary,
    format_new_project_alert,
    format_red_flag_alert,
    format_score_change_alert,
)
from app.services.alerts.telegram_bot import TelegramBot

logger = structlog.get_logger()

MIN_SCORE_FOR_ALERT = 50.0
SCORE_CHANGE_THRESHOLD = 15.0
ALERT_COOLDOWN_HOURS = 4
MAX_ALERTS_PER_CYCLE = 30


class AlertProcessor:
    """Determines which projects need alerts and dispatches them."""

    def __init__(self):
        self.bot = TelegramBot()

    async def run_alert_cycle(self, db: AsyncSession) -> dict:
        """Run a full alert cycle.

        1. Alert on new high-scoring projects
        2. Alert on significant score changes
        3. Alert on critical red flags
        4. Alert on completed AI analyses with notable results

        Returns:
            Summary dict with counts per alert type.
        """
        if not self.bot.is_configured():
            logger.warning("alerts.telegram_not_configured")
            return {"sent": 0, "skipped": True}

        new_count = await self._alert_new_projects(db)
        change_count = await self._alert_score_changes(db)
        flag_count = await self._alert_critical_flags(db)
        ai_count = await self._alert_ai_analyses(db)

        total = new_count + change_count + flag_count + ai_count
        logger.info(
            "alerts.cycle_complete",
            new_projects=new_count,
            score_changes=change_count,
            red_flags=flag_count,
            ai_analyses=ai_count,
            total=total,
        )

        return {
            "new_projects": new_count,
            "score_changes": change_count,
            "red_flags": flag_count,
            "ai_analyses": ai_count,
            "total_sent": total,
            "skipped": False,
        }

    async def send_daily_summary(self, db: AsyncSession) -> bool:
        """Send a daily summary report."""
        if not self.bot.is_configured():
            return False

        try:
            now = datetime.now(timezone.utc)
            yesterday = now - timedelta(days=1)

            total_result = await db.execute(
                select(func.count(Project.id)).where(Project.is_active.is_(True))
            )
            total_projects = total_result.scalar() or 0

            new_result = await db.execute(
                select(func.count(Project.id)).where(
                    Project.is_active.is_(True),
                    Project.discovered_at >= yesterday,
                )
            )
            new_projects = new_result.scalar() or 0

            avg_result = await db.execute(
                select(func.avg(ProjectScore.total_score))
            )
            avg_score = avg_result.scalar() or 0

            alert_result = await db.execute(
                select(func.count(AlertLog.id)).where(
                    AlertLog.sent_at >= yesterday,
                    AlertLog.delivered.is_(True),
                )
            )
            alerts_sent = alert_result.scalar() or 0

            ai_result = await db.execute(
                select(func.count(AIReport.id)).where(
                    AIReport.created_at >= yesterday,
                )
            )
            ai_analyses = ai_result.scalar() or 0

            top_result = await db.execute(
                select(Project, ProjectScore)
                .join(ProjectScore)
                .where(Project.is_active.is_(True))
                .order_by(ProjectScore.total_score.desc())
                .limit(10)
            )
            top_rows = top_result.all()
            top_projects = [
                {
                    "name": row[0].name,
                    "symbol": row[0].symbol,
                    "total_score": row[1].total_score,
                }
                for row in top_rows
            ]

            critical_result = await db.execute(
                select(RedFlag, Project)
                .join(Project)
                .where(
                    RedFlag.severity == "critical",
                    RedFlag.is_active.is_(True),
                    RedFlag.created_at >= yesterday,
                )
                .limit(5)
            )
            critical_rows = critical_result.all()
            critical_flags = [
                {
                    "project_name": row[1].name,
                    "flag_type": row[0].flag_type,
                }
                for row in critical_rows
            ]

            summary_data = {
                "total_projects": total_projects,
                "new_projects": new_projects,
                "avg_score": avg_score,
                "alerts_sent": alerts_sent,
                "ai_analyses": ai_analyses,
                "top_projects": top_projects,
                "critical_flags": critical_flags,
            }

            message = format_daily_summary(summary_data)
            result = await self.bot.send_message(message)

            if result:
                log = AlertLog(
                    project_id=top_rows[0][0].id if top_rows else None,
                    alert_type="daily_summary",
                    channel="telegram",
                    priority="low",
                    title="Daily Summary Report",
                    message=message,
                    sent_at=now,
                    delivered=True,
                    trigger_data=summary_data,
                )
                db.add(log)
                return True

        except Exception as e:
            logger.error("alerts.daily_summary_failed", error=str(e))

        return False

    async def _alert_new_projects(self, db: AsyncSession) -> int:
        """Alert on new projects with score above threshold."""
        sent = 0
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=ALERT_COOLDOWN_HOURS)

            already_alerted = select(AlertLog.project_id).where(
                AlertLog.alert_type == "new_project",
                AlertLog.delivered.is_(True),
            )

            result = await db.execute(
                select(Project, ProjectScore)
                .join(ProjectScore)
                .where(
                    Project.is_active.is_(True),
                    Project.discovered_at >= cutoff,
                    ProjectScore.total_score >= MIN_SCORE_FOR_ALERT,
                    Project.id.notin_(already_alerted),
                )
                .options(selectinload(Project.red_flags))
                .order_by(ProjectScore.total_score.desc())
                .limit(MAX_ALERTS_PER_CYCLE)
            )
            rows = result.all()

            for project, score in rows:
                try:
                    project_data = self._build_project_data(project, score)
                    message = format_new_project_alert(project_data)
                    tg_result = await self.bot.send_message(message)

                    log = AlertLog(
                        project_id=project.id,
                        alert_type="new_project",
                        channel="telegram",
                        priority="high" if score.total_score >= 70 else "medium",
                        title=f"New: {project.name} ({project.symbol})",
                        message=message,
                        sent_at=datetime.now(timezone.utc),
                        delivered=tg_result is not None,
                        error_message=None if tg_result else "Failed to send",
                        score_at_alert=score.total_score,
                        trigger_data={"score": score.total_score},
                    )
                    db.add(log)

                    if tg_result:
                        sent += 1

                except Exception as e:
                    logger.error(
                        "alerts.new_project_failed",
                        project_id=str(project.id),
                        error=str(e),
                    )

        except Exception as e:
            logger.error("alerts.new_projects_query_failed", error=str(e))

        return sent

    async def _alert_score_changes(self, db: AsyncSession) -> int:
        """Alert on significant score changes."""
        sent = 0
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=ALERT_COOLDOWN_HOURS)

            result = await db.execute(
                select(ScoreHistory)
                .where(
                    ScoreHistory.time >= cutoff,
                    func.abs(ScoreHistory.score_delta) >= SCORE_CHANGE_THRESHOLD,
                )
                .order_by(func.abs(ScoreHistory.score_delta).desc())
                .limit(MAX_ALERTS_PER_CYCLE)
            )
            score_changes = result.scalars().all()

            for change in score_changes:
                try:
                    already_sent = await self._was_alert_sent_recently(
                        db, change.project_id, "score_change", hours=ALERT_COOLDOWN_HOURS
                    )
                    if already_sent:
                        continue

                    proj_result = await db.execute(
                        select(Project, ProjectScore)
                        .join(ProjectScore)
                        .where(Project.id == change.project_id)
                        .options(selectinload(Project.red_flags))
                        .order_by(ProjectScore.created_at.desc())
                        .limit(1)
                    )
                    row = proj_result.first()
                    if not row:
                        continue

                    project, score = row
                    project_data = self._build_project_data(project, score)
                    old_score = change.total_score - (change.score_delta or 0)
                    message = format_score_change_alert(
                        project_data, old_score, change.total_score
                    )
                    tg_result = await self.bot.send_message(message)

                    log = AlertLog(
                        project_id=project.id,
                        alert_type="score_change",
                        channel="telegram",
                        priority="high" if abs(change.score_delta or 0) >= 25 else "medium",
                        title=f"Score Change: {project.name} ({change.score_delta:+.1f})",
                        message=message,
                        sent_at=datetime.now(timezone.utc),
                        delivered=tg_result is not None,
                        score_at_alert=change.total_score,
                        trigger_data={
                            "old_score": old_score,
                            "new_score": change.total_score,
                            "delta": change.score_delta,
                        },
                    )
                    db.add(log)

                    if tg_result:
                        sent += 1

                except Exception as e:
                    logger.error(
                        "alerts.score_change_failed",
                        project_id=str(change.project_id),
                        error=str(e),
                    )

        except Exception as e:
            logger.error("alerts.score_changes_query_failed", error=str(e))

        return sent

    async def _alert_critical_flags(self, db: AsyncSession) -> int:
        """Alert on newly detected critical red flags."""
        sent = 0
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=ALERT_COOLDOWN_HOURS)

            result = await db.execute(
                select(RedFlag, Project)
                .join(Project)
                .where(
                    RedFlag.severity == "critical",
                    RedFlag.is_active.is_(True),
                    RedFlag.created_at >= cutoff,
                )
                .order_by(RedFlag.created_at.desc())
                .limit(MAX_ALERTS_PER_CYCLE)
            )
            rows = result.all()

            for flag, project in rows:
                try:
                    already_sent = await self._was_alert_sent_recently(
                        db, project.id, "red_flag", hours=ALERT_COOLDOWN_HOURS
                    )
                    if already_sent:
                        continue

                    score_result = await db.execute(
                        select(ProjectScore)
                        .where(ProjectScore.project_id == project.id)
                        .order_by(ProjectScore.created_at.desc())
                        .limit(1)
                    )
                    score = score_result.scalar_one_or_none()

                    project_data = self._build_project_data(project, score)
                    flag_data = {
                        "flag_type": flag.flag_type,
                        "severity": flag.severity,
                        "description": flag.description or flag.title,
                        "detected_by": flag.detected_by,
                    }
                    message = format_red_flag_alert(project_data, flag_data)
                    tg_result = await self.bot.send_message(message)

                    log = AlertLog(
                        project_id=project.id,
                        alert_type="red_flag",
                        channel="telegram",
                        priority="critical",
                        title=f"Red Flag: {project.name} - {flag.flag_type}",
                        message=message,
                        sent_at=datetime.now(timezone.utc),
                        delivered=tg_result is not None,
                        score_at_alert=score.total_score if score else None,
                        trigger_data={
                            "flag_type": flag.flag_type,
                            "severity": flag.severity,
                            "detected_by": flag.detected_by,
                        },
                    )
                    db.add(log)

                    if tg_result:
                        sent += 1

                except Exception as e:
                    logger.error(
                        "alerts.red_flag_failed",
                        project_id=str(project.id),
                        error=str(e),
                    )

        except Exception as e:
            logger.error("alerts.critical_flags_query_failed", error=str(e))

        return sent

    async def _alert_ai_analyses(self, db: AsyncSession) -> int:
        """Alert on completed AI analyses with strong recommendations."""
        sent = 0
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=ALERT_COOLDOWN_HOURS)

            result = await db.execute(
                select(AIReport, Project)
                .join(Project, AIReport.project_id == Project.id)
                .where(
                    AIReport.report_type == "full_analysis",
                    AIReport.created_at >= cutoff,
                    AIReport.confidence >= 0.7,
                )
                .order_by(AIReport.created_at.desc())
                .limit(MAX_ALERTS_PER_CYCLE)
            )
            rows = result.all()

            for report, project in rows:
                try:
                    structured = report.structured_data or {}
                    recommendation = structured.get("recommendation", "HOLD")

                    if recommendation not in ("STRONG_BUY", "BUY", "STRONG_AVOID"):
                        continue

                    already_sent = await self._was_alert_sent_recently(
                        db, project.id, "ai_analysis", hours=ALERT_COOLDOWN_HOURS
                    )
                    if already_sent:
                        continue

                    score_result = await db.execute(
                        select(ProjectScore)
                        .where(ProjectScore.project_id == project.id)
                        .order_by(ProjectScore.created_at.desc())
                        .limit(1)
                    )
                    score = score_result.scalar_one_or_none()
                    project_data = self._build_project_data(project, score)

                    ai_result = {
                        "overall_score": report.ai_score or 0,
                        "confidence": report.confidence or 0,
                        "recommendation": recommendation,
                        "risk_level": structured.get("risk_level", "medium"),
                        "summary": report.summary or "",
                        "analysis": structured.get("analysis", {}),
                        "red_flags": structured.get("red_flags", []),
                        "provider": report.ai_model,
                        "model": report.ai_model,
                    }

                    message = format_ai_analysis_alert(project_data, ai_result)
                    tg_result = await self.bot.send_message(message)

                    log = AlertLog(
                        project_id=project.id,
                        alert_type="ai_analysis",
                        channel="telegram",
                        priority="high" if recommendation == "STRONG_BUY" else "medium",
                        title=f"AI: {project.name} → {recommendation}",
                        message=message,
                        sent_at=datetime.now(timezone.utc),
                        delivered=tg_result is not None,
                        score_at_alert=score.total_score if score else None,
                        trigger_data={
                            "ai_score": report.ai_score,
                            "recommendation": recommendation,
                            "confidence": report.confidence,
                        },
                    )
                    db.add(log)

                    if tg_result:
                        sent += 1

                except Exception as e:
                    logger.error(
                        "alerts.ai_analysis_alert_failed",
                        project_id=str(project.id),
                        error=str(e),
                    )

        except Exception as e:
            logger.error("alerts.ai_analyses_query_failed", error=str(e))

        return sent

    async def _was_alert_sent_recently(
        self, db: AsyncSession, project_id, alert_type: str, hours: int = 4
    ) -> bool:
        """Check if an alert of this type was already sent recently for this project."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        result = await db.execute(
            select(AlertLog.id)
            .where(
                AlertLog.project_id == project_id,
                AlertLog.alert_type == alert_type,
                AlertLog.delivered.is_(True),
                AlertLog.sent_at >= cutoff,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    def _build_project_data(project: Project, score: ProjectScore | None) -> dict:
        """Build a project data dict for formatting."""
        data: dict = {
            "name": project.name,
            "symbol": project.symbol,
            "blockchain": project.blockchain,
            "contract_address": project.contract_address,
            "source": project.source,
        }

        if score:
            data["total_score"] = score.total_score
            data["engine_scores"] = {
                "engine1": score.engine1_score,
                "engine2": score.engine2_score,
                "engine3": score.engine3_score,
                "engine4": score.engine4_score,
                "engine5": score.engine5_score,
            }
            data["red_flag_count"] = score.red_flag_count

        return data

    async def close(self) -> None:
        await self.bot.close()
