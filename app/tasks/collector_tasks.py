import asyncio

import structlog

from app.core.database import async_session_factory
from app.services.processors.scan_processor import ScanProcessor
from app.tasks.celery_app import celery_app

logger = structlog.get_logger()


def _run_async(coro):
    """Run an async function from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _scan_new_projects():
    processor = ScanProcessor()
    try:
        async with async_session_factory() as session:
            try:
                dex_count = await processor.scan_new_projects_dexscreener(session)
                cg_count = await processor.scan_trending_coingecko(session)
                gt_count = await processor.scan_trending_geckoterminal(session)
                dl_count = await processor.scan_protocols_defillama(session)
                await session.commit()
                logger.info(
                    "task.scan_new_projects.done",
                    dexscreener_new=dex_count,
                    coingecko_new=cg_count,
                    geckoterminal_new=gt_count,
                    defillama_new=dl_count,
                )
            except Exception:
                await session.rollback()
                raise
    finally:
        await processor.close_all()


async def _collect_market_data():
    processor = ScanProcessor()
    try:
        async with async_session_factory() as session:
            try:
                dex_count = await processor.collect_market_data_dexscreener(session)
                cg_count = await processor.collect_market_data_coingecko(session)
                gt_count = await processor.collect_market_data_geckoterminal(session)
                cmc_count = await processor.collect_market_data_coinmarketcap(session)
                await session.commit()
                logger.info(
                    "task.collect_market_data.done",
                    dexscreener=dex_count,
                    coingecko=cg_count,
                    geckoterminal=gt_count,
                    coinmarketcap=cmc_count,
                )
            except Exception:
                await session.rollback()
                raise
    finally:
        await processor.close_all()


async def _collect_social_data():
    processor = ScanProcessor()
    try:
        async with async_session_factory() as session:
            try:
                reddit_count = await processor.collect_social_data_reddit(session)
                await session.commit()
                logger.info("task.collect_social_data.done", reddit=reddit_count)
            except Exception:
                await session.rollback()
                raise
    finally:
        await processor.close_all()


async def _collect_onchain_data():
    processor = ScanProcessor()
    try:
        async with async_session_factory() as session:
            try:
                goplus_count = await processor.collect_onchain_goplus(session)
                await session.commit()
                logger.info("task.collect_onchain_data.done", goplus=goplus_count)
            except Exception:
                await session.rollback()
                raise
    finally:
        await processor.close_all()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def scan_new_projects(self):
    """Engine 1: Scan launchpads and DEXes for new projects."""
    logger.info("task.scan_new_projects.start")
    try:
        _run_async(_scan_new_projects())
    except Exception as exc:
        logger.error("task.scan_new_projects.error", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def collect_market_data(self):
    """Engine 2: Collect market data for monitored projects."""
    logger.info("task.collect_market_data.start")
    try:
        _run_async(_collect_market_data())
    except Exception as exc:
        logger.error("task.collect_market_data.error", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def collect_social_data(self):
    """Engine 3: Collect social media data."""
    logger.info("task.collect_social_data.start")
    try:
        _run_async(_collect_social_data())
    except Exception as exc:
        logger.error("task.collect_social_data.error", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def collect_onchain_data(self):
    """Engine 4: Collect on-chain data."""
    logger.info("task.collect_onchain_data.start")
    try:
        _run_async(_collect_onchain_data())
    except Exception as exc:
        logger.error("task.collect_onchain_data.error", error=str(exc))
        raise self.retry(exc=exc)


async def _cleanup_old_data():
    from app.services.processors.cleanup_processor import CleanupProcessor

    processor = CleanupProcessor()
    async with async_session_factory() as session:
        try:
            result = await processor.run_full_cleanup(session)
            await session.commit()
            logger.info("task.cleanup_old_data.done", **result)
        except Exception:
            await session.rollback()
            raise


@celery_app.task(bind=True, max_retries=1, default_retry_delay=300)
def cleanup_old_data(self):
    """Archive old data to cold storage and clean up stale records."""
    logger.info("task.cleanup_old_data.start")
    try:
        _run_async(_cleanup_old_data())
    except Exception as exc:
        logger.error("task.cleanup_old_data.error", error=str(exc))
        raise self.retry(exc=exc)
