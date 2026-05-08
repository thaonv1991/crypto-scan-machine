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


async def _scan_launchpads():
    """Scan launchpads for upcoming and new token launches."""
    from app.services.collectors.binance_launchpad import BinanceLaunchpadCollector
    from app.services.collectors.daomaker import DAOMakerCollector
    from app.services.collectors.pinksale import PinksaleCollector
    from app.services.collectors.pumpfun import PumpFunCollector

    collectors = [
        ("pumpfun", PumpFunCollector()),
        ("pinksale", PinksaleCollector()),
        ("daomaker", DAOMakerCollector()),
        ("binance_launchpad", BinanceLaunchpadCollector()),
    ]
    total = 0
    for name, collector in collectors:
        try:
            results = await collector.collect()
            total += len(results)
            logger.info("task.scan_launchpads.source_done", source=name, count=len(results))
        except Exception as e:
            logger.error("task.scan_launchpads.source_error", source=name, error=str(e))
        finally:
            await collector.close()
    return total


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


async def _collect_social_intelligence():
    """Collect social intelligence from YouTube and LunarCrush."""
    from app.services.collectors.lunarcrush import LunarCrushCollector
    from app.services.collectors.youtube import YouTubeCollector

    results = {"youtube": 0, "lunarcrush": 0}

    yt = YouTubeCollector()
    try:
        if yt.is_configured():
            data = await yt.collect(query="crypto new token launch", max_results=5)
            results["youtube"] = len(data)
    except Exception as e:
        logger.error("task.social_intelligence.youtube_error", error=str(e))
    finally:
        await yt.close()

    lc = LunarCrushCollector()
    try:
        if lc.is_configured():
            data = await lc.collect(mode="trending")
            results["lunarcrush"] = len(data)
    except Exception as e:
        logger.error("task.social_intelligence.lunarcrush_error", error=str(e))
    finally:
        await lc.close()

    return results


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


async def _collect_multichain_onchain():
    """Collect on-chain data from BSCScan, Solscan, Helius."""
    from app.services.collectors.bscscan import BSCScanCollector
    from app.services.collectors.helius import HeliusCollector
    from app.services.collectors.solscan import SolscanCollector

    results = {"bscscan": 0, "solscan": 0, "helius": 0}
    collectors_to_close = []

    bsc = BSCScanCollector()
    collectors_to_close.append(bsc)
    if bsc.is_configured():
        try:
            logger.info("task.multichain_onchain.bscscan_ready")
            results["bscscan"] = 1
        except Exception as e:
            logger.error("task.multichain_onchain.bscscan_error", error=str(e))

    sol = SolscanCollector()
    collectors_to_close.append(sol)
    if sol.is_configured():
        try:
            logger.info("task.multichain_onchain.solscan_ready")
            results["solscan"] = 1
        except Exception as e:
            logger.error("task.multichain_onchain.solscan_error", error=str(e))

    hel = HeliusCollector()
    collectors_to_close.append(hel)
    if hel.is_configured():
        try:
            logger.info("task.multichain_onchain.helius_ready")
            results["helius"] = 1
        except Exception as e:
            logger.error("task.multichain_onchain.helius_error", error=str(e))

    for c in collectors_to_close:
        await c.close()

    return results


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def scan_new_projects(self):
    """Engine 1: Scan launchpads and DEXes for new projects."""
    logger.info("task.scan_new_projects.start")
    try:
        _run_async(_scan_new_projects())
    except Exception as exc:
        logger.error("task.scan_new_projects.error", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def scan_launchpads(self):
    """Scan launchpads: Pump.fun, Pinksale, DAO Maker, Binance Launchpad."""
    logger.info("task.scan_launchpads.start")
    try:
        total = _run_async(_scan_launchpads())
        logger.info("task.scan_launchpads.done", total=total)
    except Exception as exc:
        logger.error("task.scan_launchpads.error", error=str(exc))
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


@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def collect_social_intelligence(self):
    """Collect social intelligence from YouTube and LunarCrush."""
    logger.info("task.collect_social_intelligence.start")
    try:
        results = _run_async(_collect_social_intelligence())
        logger.info("task.collect_social_intelligence.done", **results)
    except Exception as exc:
        logger.error("task.collect_social_intelligence.error", error=str(exc))
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


@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def collect_multichain_onchain(self):
    """Collect on-chain data from BSCScan, Solscan, Helius."""
    logger.info("task.collect_multichain_onchain.start")
    try:
        results = _run_async(_collect_multichain_onchain())
        logger.info("task.collect_multichain_onchain.done", **results)
    except Exception as exc:
        logger.error("task.collect_multichain_onchain.error", error=str(exc))
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
