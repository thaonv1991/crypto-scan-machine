import asyncio

import structlog

from app.core.database import async_session_factory
from app.services.processors.scoring_processor import ScoringProcessor
from app.tasks.celery_app import celery_app

logger = structlog.get_logger()


def _run_async(coro):
    """Run an async function from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _calculate_all_scores():
    processor = ScoringProcessor()
    async with async_session_factory() as session:
        try:
            scored = await processor.calculate_all_scores(session)
            await session.commit()
            logger.info("task.calculate_all_scores.done", scored=scored)
        except Exception:
            await session.rollback()
            raise


async def _calculate_project_score(project_id: str):
    processor = ScoringProcessor()
    async with async_session_factory() as session:
        try:
            result = await processor.calculate_project_score(session, project_id)
            await session.commit()
            logger.info(
                "task.calculate_project_score.done",
                project_id=project_id,
                score=result["total_score"] if result else None,
            )
        except Exception:
            await session.rollback()
            raise


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def calculate_all_scores(self):
    """Recalculate scores for all active projects."""
    logger.info("task.calculate_all_scores.start")
    try:
        _run_async(_calculate_all_scores())
    except Exception as exc:
        logger.error("task.calculate_all_scores.error", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def run_ai_analysis(self):
    """Engine 5: Run AI analysis on top-scoring projects."""
    logger.info("task.run_ai_analysis.start")
    # TODO: Implement in Phase 3
    logger.info("task.run_ai_analysis.complete")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def calculate_project_score(self, project_id: str):
    """Calculate score for a single project."""
    logger.info("task.calculate_project_score.start", project_id=project_id)
    try:
        _run_async(_calculate_project_score(project_id))
    except Exception as exc:
        logger.error("task.calculate_project_score.error", project_id=project_id, error=str(exc))
        raise self.retry(exc=exc)
