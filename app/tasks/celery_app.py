from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "crypto_scan",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.collector_tasks",
        "app.tasks.scoring_tasks",
        "app.tasks.alert_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    result_expires=3600,
    task_soft_time_limit=300,
    task_time_limit=600,
)

celery_app.conf.beat_schedule = {
    # 🚀 RE-ENABLED: Momentum & Trending Engines (For old coins suddenly pumping)
    # Re-activated to complement the Realtime Web3 Listener
    "scan-trending-projects": {
        "task": "app.tasks.collector_tasks.scan_new_projects",
        "schedule": crontab(minute="*/5"), # Scans DexScreener/CoinGecko Trending every 5 mins
    },
    "scan-launchpads": {
        "task": "app.tasks.collector_tasks.scan_launchpads",
        "schedule": crontab(minute="*/15"),
    },
    # Engine 2: Collect market data every 5 minutes
    "collect-market-data": {
        "task": "app.tasks.collector_tasks.collect_market_data",
        "schedule": crontab(minute="*/5"),
    },
    # Engine 3: Collect social data every 30 minutes
    "collect-social-data": {
        "task": "app.tasks.collector_tasks.collect_social_data",
        "schedule": crontab(minute="*/30"),
    },
    # Social intelligence (YouTube, LunarCrush) every hour
    "collect-social-intelligence": {
        "task": "app.tasks.collector_tasks.collect_social_intelligence",
        "schedule": crontab(minute=15),
    },
    # Engine 4: Collect on-chain data every 10 minutes
    "collect-onchain-data": {
        "task": "app.tasks.collector_tasks.collect_onchain_data",
        "schedule": crontab(minute="*/10"),
    },
    # Multi-chain on-chain data (BSCScan, Solscan, Helius) every 15 minutes
    "collect-multichain-onchain": {
        "task": "app.tasks.collector_tasks.collect_multichain_onchain",
        "schedule": crontab(minute="*/15"),
    },
    # Scoring: Recalculate scores every 15 minutes
    "calculate-scores": {
        "task": "app.tasks.scoring_tasks.calculate_all_scores",
        "schedule": crontab(minute="*/15"),
    },
    # AI Analysis: Run every hour
    "ai-analysis": {
        "task": "app.tasks.scoring_tasks.run_ai_analysis",
        "schedule": crontab(minute=0),
    },
    # Alerts: Send alerts every 20 minutes
    "send-alerts": {
        "task": "app.tasks.alert_tasks.send_alerts",
        "schedule": crontab(minute="*/20"),
    },
    # Daily summary at 8 AM UTC
    "daily-summary": {
        "task": "app.tasks.alert_tasks.send_daily_summary",
        "schedule": crontab(hour=8, minute=0),
    },
    # 🧠 Autonomous Agent Learning Loop: Runs daily at 1 AM
    "agent-reflection-loop": {
        "task": "app.tasks.scoring_tasks.run_agent_learning_loop",
        "schedule": crontab(hour=1, minute=0),
    },
    # Cleanup: Archive old data daily at 3 AM
    "cleanup-old-data": {
        "task": "app.tasks.collector_tasks.cleanup_old_data",
        "schedule": crontab(hour=3, minute=0),
    },
}
