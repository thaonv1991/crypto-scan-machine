import asyncio

import structlog

from app.core.database import async_session_factory
from app.services.processors.alert_processor import AlertProcessor
from app.tasks.celery_app import celery_app

logger = structlog.get_logger()


def _run_async(coro):
    """Run an async function from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _send_alerts():
    processor = AlertProcessor()
    async with async_session_factory() as session:
        try:
            result = await processor.run_alert_cycle(session)
            await session.commit()
            logger.info("task.send_alerts.done", **result)
        except Exception:
            await session.rollback()
            raise
        finally:
            await processor.close()


async def _send_daily_summary():
    processor = AlertProcessor()
    async with async_session_factory() as session:
        try:
            sent = await processor.send_daily_summary(session)
            await session.commit()
            logger.info("task.daily_summary.done", sent=sent)
        except Exception:
            await session.rollback()
            raise
        finally:
            await processor.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_alerts(self):
    """Send alerts for notable project events."""
    logger.info("task.send_alerts.start")
    try:
        _run_async(_send_alerts())
    except Exception as exc:
        logger.error("task.send_alerts.error", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def send_daily_summary(self):
    """Send daily summary report via Telegram."""
    logger.info("task.daily_summary.start")
    try:
        _run_async(_send_daily_summary())
    except Exception as exc:
        logger.error("task.daily_summary.error", error=str(exc))
        raise self.retry(exc=exc)
