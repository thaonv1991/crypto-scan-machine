import structlog

from app.tasks.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def calculate_all_scores(self):
    """Recalculate scores for all active projects."""
    logger.info("task.calculate_all_scores.start")
    # TODO: Implement in Phase 2
    logger.info("task.calculate_all_scores.complete")


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
    # TODO: Implement in Phase 2
    logger.info("task.calculate_project_score.complete", project_id=project_id)
