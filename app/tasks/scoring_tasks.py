import asyncio

import structlog

from app.core.database import async_session_factory
from app.services.processors.ai_processor import AIAnalysisProcessor
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


async def _run_ai_analysis():
    processor = AIAnalysisProcessor()
    async with async_session_factory() as session:
        try:
            result = await processor.run_analysis_cycle(session)
            await session.commit()
            logger.info("task.run_ai_analysis.done", **result)
        except Exception:
            await session.rollback()
            raise
        finally:
            await processor.close_all()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def run_ai_analysis(self):
    """Engine 5: Run AI analysis on top-scoring projects."""
    logger.info("task.run_ai_analysis.start")
    try:
        _run_async(_run_ai_analysis())
    except Exception as exc:
        logger.error("task.run_ai_analysis.error", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def calculate_project_score(self, project_id: str):
    """Calculate score for a single project."""
    logger.info("task.calculate_project_score.start", project_id=project_id)
    try:
        _run_async(_calculate_project_score(project_id))
    except Exception as exc:
        logger.error("task.calculate_project_score.error", project_id=project_id, error=str(exc))
        raise self.retry(exc=exc)


async def _score_new_realtime_token(token_data: dict):
    # This is where the AI and Smart Contract scanner kicks in immediately
    # after a token is discovered via WebSocket
    from app.services.processors.realtime_auditor import RealtimeAuditor
    
    auditor = RealtimeAuditor()
    async with async_session_factory() as session:
        try:
            logger.info("⚡ Realtime AI Scoring Initiated", token=token_data['address'])
            result = await auditor.run_instant_audit(session, token_data)
            await session.commit()
            
            if result:
@celery_app.task(bind=True, max_retries=1, default_retry_delay=60)
def score_new_realtime_token(self, token_data: dict):
    """
    Instantly triggered by Web3 Listener when a new pair is created.
    """
    logger.info("task.score_new_realtime_token.start", token=token_data.get('address'))
    try:
        from app.services.processors.realtime_auditor import RealtimeAuditor
        auditor = RealtimeAuditor()
        
        async def run():
            async with async_session_factory() as db:
                return await auditor.run_instant_audit(db, token_data)
                
        result = _run_async(run())
        logger.info("task.score_new_realtime_token.done", result=result)
    except Exception as exc:
        logger.error("task.score_new_realtime_token.error", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=1, default_retry_delay=300)
def run_agent_learning_loop(self):
    """
    Runs daily to reflect on past AI predictions vs actual market outcomes.
    """
    logger.info("task.run_agent_learning_loop.start")
    try:
        from app.services.ai.agent_learner import crypto_agent
        async def run():
            async with async_session_factory() as db:
                await crypto_agent.self_reflection_loop(db)
        _run_async(run())
        logger.info("task.run_agent_learning_loop.done")
    except Exception as exc:
        logger.error("task.run_agent_learning_loop.error", error=str(exc))
        raise self.retry(exc=exc)
