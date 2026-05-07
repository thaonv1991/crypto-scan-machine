import structlog

from app.tasks.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def scan_new_projects(self):
    """Engine 1: Scan launchpads and DEXes for new projects."""
    logger.info("task.scan_new_projects.start")
    # TODO: Implement in Phase 1
    logger.info("task.scan_new_projects.complete")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def collect_market_data(self):
    """Engine 2: Collect market data for monitored projects."""
    logger.info("task.collect_market_data.start")
    # TODO: Implement in Phase 1
    logger.info("task.collect_market_data.complete")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def collect_social_data(self):
    """Engine 3: Collect social media data."""
    logger.info("task.collect_social_data.start")
    # TODO: Implement in Phase 1
    logger.info("task.collect_social_data.complete")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def collect_onchain_data(self):
    """Engine 4: Collect on-chain data."""
    logger.info("task.collect_onchain_data.start")
    # TODO: Implement in Phase 1
    logger.info("task.collect_onchain_data.complete")


@celery_app.task(bind=True, max_retries=1, default_retry_delay=300)
def cleanup_old_data(self):
    """Archive old data to cold storage."""
    logger.info("task.cleanup_old_data.start")
    # TODO: Implement in Phase 6
    logger.info("task.cleanup_old_data.complete")
