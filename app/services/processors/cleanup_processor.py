import io
import json
import time
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import AlertLog, RedFlag
from app.models.onchain import OnchainData, WhaleActivity
from app.models.project import Project, ProjectScore
from app.models.timeseries import MarketData, ScoreHistory, SocialData

logger = structlog.get_logger()

# Default retention periods (days)
MARKET_DATA_RETENTION_DAYS = 90
SOCIAL_DATA_RETENTION_DAYS = 60
SCORE_HISTORY_RETENTION_DAYS = 180
ALERT_LOG_RETENTION_DAYS = 90
INACTIVE_PROJECT_ARCHIVE_DAYS = 30
WHALE_ACTIVITY_RETENTION_DAYS = 60
ONCHAIN_DATA_RETENTION_DAYS = 90


class CleanupProcessor:
    """Handles data cleanup, archival, and cold storage operations."""

    def __init__(self):
        self.minio_client = None
        self._init_minio()

    def _init_minio(self):
        """Initialize MinIO client for cold storage."""
        try:
            from minio import Minio

            from app.core.config import settings

            self.minio_client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=False,
            )

            # Ensure bucket exists
            if not self.minio_client.bucket_exists(settings.minio_bucket):
                self.minio_client.make_bucket(settings.minio_bucket)
                logger.info("cleanup.minio.bucket_created", bucket=settings.minio_bucket)

            logger.info("cleanup.minio.connected", endpoint=settings.minio_endpoint)
        except ImportError:
            logger.warning("cleanup.minio.not_installed", message="minio package not installed, cold storage disabled")
            self.minio_client = None
        except Exception as e:
            logger.warning("cleanup.minio.connection_failed", error=str(e))
            self.minio_client = None

    async def run_full_cleanup(self, db: AsyncSession) -> dict:
        """Run complete data cleanup cycle."""
        start_time = time.monotonic()
        results = {
            "market_data_deleted": 0,
            "social_data_deleted": 0,
            "score_history_deleted": 0,
            "alert_logs_deleted": 0,
            "whale_activities_deleted": 0,
            "onchain_data_deleted": 0,
            "projects_archived": 0,
            "red_flags_resolved": 0,
            "cold_storage_bytes": 0,
        }

        # 1. Archive old market data to cold storage, then delete
        results["market_data_deleted"] = await self._cleanup_market_data(db)

        # 2. Cleanup old social data
        results["social_data_deleted"] = await self._cleanup_social_data(db)

        # 3. Cleanup old score history
        results["score_history_deleted"] = await self._cleanup_score_history(db)

        # 4. Cleanup old alert logs
        results["alert_logs_deleted"] = await self._cleanup_alert_logs(db)

        # 5. Cleanup old whale activities
        results["whale_activities_deleted"] = await self._cleanup_whale_activities(db)

        # 6. Cleanup old onchain data
        results["onchain_data_deleted"] = await self._cleanup_onchain_data(db)

        # 7. Archive inactive projects
        results["projects_archived"] = await self._archive_inactive_projects(db)

        # 8. Resolve old red flags
        results["red_flags_resolved"] = await self._resolve_old_red_flags(db)

        # 9. Archive data to cold storage
        results["cold_storage_bytes"] = await self._archive_to_cold_storage(db)

        elapsed = time.monotonic() - start_time
        results["duration_seconds"] = round(elapsed, 2)  # type: ignore[assignment]

        logger.info("cleanup.full_cleanup.done", **results)
        return results

    async def _cleanup_market_data(self, db: AsyncSession) -> int:
        """Delete market data older than retention period."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=MARKET_DATA_RETENTION_DAYS)

        # Archive to cold storage before deletion
        if self.minio_client:
            await self._archive_timeseries_to_minio(
                db, MarketData, "market_data", cutoff
            )

        result = await db.execute(
            delete(MarketData).where(MarketData.time < cutoff)
        )
        count = int(result.rowcount or 0)  # type: ignore[attr-defined]
        if count > 0:
            logger.info("cleanup.market_data.deleted", count=count, cutoff=cutoff.isoformat())
        return count

    async def _cleanup_social_data(self, db: AsyncSession) -> int:
        """Delete social data older than retention period."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=SOCIAL_DATA_RETENTION_DAYS)

        if self.minio_client:
            await self._archive_timeseries_to_minio(
                db, SocialData, "social_data", cutoff
            )

        result = await db.execute(
            delete(SocialData).where(SocialData.time < cutoff)
        )
        count = int(result.rowcount or 0)  # type: ignore[attr-defined]
        if count > 0:
            logger.info("cleanup.social_data.deleted", count=count, cutoff=cutoff.isoformat())
        return count

    async def _cleanup_score_history(self, db: AsyncSession) -> int:
        """Delete score history older than retention period."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=SCORE_HISTORY_RETENTION_DAYS)

        if self.minio_client:
            await self._archive_timeseries_to_minio(
                db, ScoreHistory, "score_history", cutoff
            )

        result = await db.execute(
            delete(ScoreHistory).where(ScoreHistory.time < cutoff)
        )
        count = int(result.rowcount or 0)  # type: ignore[attr-defined]
        if count > 0:
            logger.info("cleanup.score_history.deleted", count=count, cutoff=cutoff.isoformat())
        return count

    async def _cleanup_alert_logs(self, db: AsyncSession) -> int:
        """Delete old alert logs."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=ALERT_LOG_RETENTION_DAYS)
        result = await db.execute(
            delete(AlertLog).where(AlertLog.created_at < cutoff)
        )
        count = int(result.rowcount or 0)  # type: ignore[attr-defined]
        if count > 0:
            logger.info("cleanup.alert_logs.deleted", count=count)
        return count

    async def _cleanup_whale_activities(self, db: AsyncSession) -> int:
        """Delete old whale activity records."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=WHALE_ACTIVITY_RETENTION_DAYS)
        result = await db.execute(
            delete(WhaleActivity).where(WhaleActivity.created_at < cutoff)
        )
        count = int(result.rowcount or 0)  # type: ignore[attr-defined]
        if count > 0:
            logger.info("cleanup.whale_activities.deleted", count=count)
        return count

    async def _cleanup_onchain_data(self, db: AsyncSession) -> int:
        """Delete old onchain data snapshots, keeping latest per project."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=ONCHAIN_DATA_RETENTION_DAYS)

        # Get the latest onchain_data ID for each project to preserve
        latest_subq = (
            select(
                OnchainData.project_id,
                func.max(OnchainData.created_at).label("max_created"),
            )
            .group_by(OnchainData.project_id)
            .subquery()
        )

        # Delete old entries except the latest per project
        old_ids_query = (
            select(OnchainData.id)
            .join(
                latest_subq,
                (OnchainData.project_id == latest_subq.c.project_id)
                & (OnchainData.created_at == latest_subq.c.max_created),
                isouter=True,
            )
            .where(
                OnchainData.created_at < cutoff,
                latest_subq.c.project_id.is_(None),
            )
        )

        result = await db.execute(old_ids_query)
        old_ids = [row[0] for row in result.fetchall()]

        if old_ids:
            await db.execute(delete(OnchainData).where(OnchainData.id.in_(old_ids)))
            logger.info("cleanup.onchain_data.deleted", count=len(old_ids))

        return len(old_ids)

    async def _archive_inactive_projects(self, db: AsyncSession) -> int:
        """Archive projects that have been inactive for too long."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=INACTIVE_PROJECT_ARCHIVE_DAYS)

        result = await db.execute(
            update(Project)
            .where(
                Project.is_active.is_(True),
                Project.status == "new",
                Project.discovered_at < cutoff,
            )
            .values(status="archived", is_active=False)
        )
        count = int(result.rowcount or 0)  # type: ignore[attr-defined]
        if count > 0:
            logger.info("cleanup.projects.archived", count=count)
        return count

    async def _resolve_old_red_flags(self, db: AsyncSession) -> int:
        """Auto-resolve red flags older than 30 days that are still active."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)

        result = await db.execute(
            update(RedFlag)
            .where(
                RedFlag.is_active.is_(True),
                RedFlag.created_at < cutoff,
                RedFlag.severity != "critical",
            )
            .values(is_active=False, resolved_at=datetime.now(timezone.utc))
        )
        count = int(result.rowcount or 0)  # type: ignore[attr-defined]
        if count > 0:
            logger.info("cleanup.red_flags.resolved", count=count)
        return count

    async def _archive_timeseries_to_minio(
        self,
        db: AsyncSession,
        model,
        table_name: str,
        cutoff: datetime,
    ) -> int:
        """Archive time-series data to MinIO cold storage before deletion."""
        if not self.minio_client:
            return 0

        try:
            from app.core.config import settings

            # Query data to archive
            query = select(model).where(model.time < cutoff).limit(10000)
            result = await db.execute(query)
            rows = result.scalars().all()

            if not rows:
                return 0

            # Serialize to JSON lines
            records = []
            for row in rows:
                record = {}
                for col in row.__table__.columns:
                    val = getattr(row, col.name)
                    if isinstance(val, datetime):
                        val = val.isoformat()
                    elif hasattr(val, "hex"):
                        val = str(val)
                    record[col.name] = val
                records.append(json.dumps(record))

            data = "\n".join(records)
            data_bytes = data.encode("utf-8")

            # Upload to MinIO
            now = datetime.now(timezone.utc)
            object_name = f"archive/{table_name}/{now.strftime('%Y/%m/%d')}/{table_name}_{now.strftime('%H%M%S')}.jsonl"

            self.minio_client.put_object(
                settings.minio_bucket,
                object_name,
                io.BytesIO(data_bytes),
                len(data_bytes),
                content_type="application/jsonl",
            )

            logger.info(
                "cleanup.cold_storage.archived",
                table=table_name,
                records=len(records),
                bytes=len(data_bytes),
                object=object_name,
            )
            return len(data_bytes)

        except Exception as e:
            logger.error("cleanup.cold_storage.error", table=table_name, error=str(e))
            return 0

    async def _archive_to_cold_storage(self, db: AsyncSession) -> int:
        """Archive old project scores to cold storage."""
        if not self.minio_client:
            return 0

        total_bytes = 0
        cutoff = datetime.now(timezone.utc) - timedelta(days=SCORE_HISTORY_RETENTION_DAYS)

        try:
            from app.core.config import settings

            # Archive old project scores
            query = (
                select(ProjectScore)
                .where(ProjectScore.created_at < cutoff)
                .limit(5000)
            )
            result = await db.execute(query)
            rows = result.scalars().all()

            if rows:
                records = []
                for row in rows:
                    record = {}
                    for col in row.__table__.columns:
                        val = getattr(row, col.name)
                        if isinstance(val, datetime):
                            val = val.isoformat()
                        elif hasattr(val, "hex"):
                            val = str(val)
                        record[col.name] = val
                    records.append(json.dumps(record))

                data = "\n".join(records)
                data_bytes = data.encode("utf-8")

                now = datetime.now(timezone.utc)
                object_name = f"archive/project_scores/{now.strftime('%Y/%m/%d')}/scores_{now.strftime('%H%M%S')}.jsonl"

                self.minio_client.put_object(
                    settings.minio_bucket,
                    object_name,
                    io.BytesIO(data_bytes),
                    len(data_bytes),
                    content_type="application/jsonl",
                )

                # Delete archived scores
                archived_ids = [row.id for row in rows]
                await db.execute(
                    delete(ProjectScore).where(ProjectScore.id.in_(archived_ids))
                )

                total_bytes += len(data_bytes)
                logger.info(
                    "cleanup.cold_storage.scores_archived",
                    records=len(records),
                    bytes=len(data_bytes),
                )

        except Exception as e:
            logger.error("cleanup.cold_storage.scores_error", error=str(e))

        return total_bytes

    async def get_storage_summary(self, db: AsyncSession) -> dict:
        """Get summary of data volumes for monitoring."""
        now = datetime.now(timezone.utc)

        market_total = (await db.execute(
            select(func.count()).select_from(MarketData)
        )).scalar() or 0

        social_total = (await db.execute(
            select(func.count()).select_from(SocialData)
        )).scalar() or 0

        score_total = (await db.execute(
            select(func.count()).select_from(ScoreHistory)
        )).scalar() or 0

        alert_total = (await db.execute(
            select(func.count(AlertLog.id))
        )).scalar() or 0

        oldest_market = (await db.execute(
            select(func.min(MarketData.time))
        )).scalar()

        return {
            "market_data_rows": market_total,
            "social_data_rows": social_total,
            "score_history_rows": score_total,
            "alert_log_rows": alert_total,
            "oldest_market_data": oldest_market.isoformat() if oldest_market else None,
            "retention_config": {
                "market_data_days": MARKET_DATA_RETENTION_DAYS,
                "social_data_days": SOCIAL_DATA_RETENTION_DAYS,
                "score_history_days": SCORE_HISTORY_RETENTION_DAYS,
                "alert_log_days": ALERT_LOG_RETENTION_DAYS,
            },
            "cold_storage_enabled": self.minio_client is not None,
            "checked_at": now.isoformat(),
        }
