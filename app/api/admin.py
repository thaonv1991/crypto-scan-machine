import uuid
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.analysis import AIReport, AlertLog, DataSource, RedFlag, UserWatchlist
from app.models.project import Project, ProjectScore
from app.models.timeseries import MarketData
from app.schemas.admin import (
    AIReportResponse,
    AlertConfigResponse,
    AlertConfigUpdate,
    BulkActionResponse,
    BulkStatusUpdate,
    CleanupConfigResponse,
    DataSourceCreate,
    DataSourceListResponse,
    DataSourceResponse,
    DataSourceUpdate,
    ProjectUpdate,
    ScoringWeightsConfig,
    ScoringWeightsResponse,
    SystemStatusResponse,
    TaskTriggerRequest,
    TaskTriggerResponse,
    WatchlistAdd,
    WatchlistResponse,
    WatchlistUpdate,
)
from app.schemas.project import ProjectResponse

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
logger = structlog.get_logger()

# In-memory config store (will persist via Redis in production)
_alert_config = {
    "min_score_for_alert": 50.0,
    "score_change_threshold": 15.0,
    "alert_cooldown_hours": 4,
    "max_alerts_per_cycle": 30,
    "alerts_enabled": True,
}

_scoring_weights = {
    "engine1_weight": 0.15,
    "engine2_weight": 0.30,
    "engine3_weight": 0.15,
    "engine4_weight": 0.25,
    "engine5_weight": 0.15,
}

_cleanup_config = {
    "market_data_retention_days": 90,
    "social_data_retention_days": 60,
    "score_history_retention_days": 180,
    "inactive_project_archive_days": 30,
    "last_cleanup": None,
}


# ==================== Project Management ====================


@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a project's details."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    await db.flush()
    await db.refresh(project)
    logger.info("admin.project.updated", project_id=str(project_id), fields=list(update_data.keys()))
    return ProjectResponse.model_validate(project)


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: uuid.UUID,
    hard_delete: bool = Query(False, description="Permanently delete instead of soft-delete"),
    db: AsyncSession = Depends(get_db),
):
    """Delete or deactivate a project."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if hard_delete:
        await db.delete(project)
        logger.info("admin.project.hard_deleted", project_id=str(project_id), name=project.name)
        return {"message": f"Project '{project.name}' permanently deleted"}
    else:
        project.is_active = False
        project.status = "archived"
        await db.flush()
        logger.info("admin.project.archived", project_id=str(project_id), name=project.name)
        return {"message": f"Project '{project.name}' archived"}


@router.post("/projects/bulk-status", response_model=BulkActionResponse)
async def bulk_update_status(
    data: BulkStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Bulk update project status."""
    values: dict = {"status": data.status}
    if data.is_active is not None:
        values["is_active"] = data.is_active

    result = await db.execute(
        update(Project).where(Project.id.in_(data.project_ids)).values(**values)
    )
    count = result.rowcount
    logger.info("admin.projects.bulk_status", count=count, status=data.status)
    return BulkActionResponse(
        updated=count,
        message=f"Updated {count} projects to status '{data.status}'",
    )


@router.post("/projects/{project_id}/rescan")
async def trigger_project_rescan(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Trigger an immediate rescan for a specific project."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    from app.tasks.scoring_tasks import calculate_project_score
    task = calculate_project_score.delay(str(project_id))

    logger.info("admin.project.rescan_triggered", project_id=str(project_id))
    return {
        "task_id": task.id,
        "message": f"Rescan triggered for '{project.name}'",
    }


# ==================== Data Source / API Key Management ====================


@router.get("/data-sources", response_model=DataSourceListResponse)
async def list_data_sources(db: AsyncSession = Depends(get_db)):
    """List all configured data sources."""
    result = await db.execute(select(DataSource).order_by(DataSource.name))
    sources = result.scalars().all()
    return DataSourceListResponse(
        total=len(sources),
        sources=[DataSourceResponse.model_validate(s) for s in sources],
    )


@router.post("/data-sources", response_model=DataSourceResponse, status_code=201)
async def create_data_source(
    data: DataSourceCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a new data source configuration."""
    existing = await db.execute(
        select(DataSource).where(DataSource.name == data.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Data source '{data.name}' already exists")

    source = DataSource(**data.model_dump())
    db.add(source)
    await db.flush()
    await db.refresh(source)
    logger.info("admin.datasource.created", name=data.name)
    return DataSourceResponse.model_validate(source)


@router.put("/data-sources/{source_id}", response_model=DataSourceResponse)
async def update_data_source(
    source_id: uuid.UUID,
    data: DataSourceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a data source configuration."""
    result = await db.execute(select(DataSource).where(DataSource.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(source, field, value)

    await db.flush()
    await db.refresh(source)
    logger.info("admin.datasource.updated", source_id=str(source_id), fields=list(update_data.keys()))
    return DataSourceResponse.model_validate(source)


@router.delete("/data-sources/{source_id}")
async def delete_data_source(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a data source."""
    result = await db.execute(select(DataSource).where(DataSource.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")

    await db.delete(source)
    logger.info("admin.datasource.deleted", source_id=str(source_id), name=source.name)
    return {"message": f"Data source '{source.name}' deleted"}


@router.post("/data-sources/{source_id}/reset-errors")
async def reset_data_source_errors(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Reset error counters for a data source."""
    result = await db.execute(select(DataSource).where(DataSource.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")

    source.error_count = 0
    source.consecutive_errors = 0
    source.last_error = None
    await db.flush()
    logger.info("admin.datasource.errors_reset", source_id=str(source_id))
    return {"message": f"Error counters reset for '{source.name}'"}


# ==================== Scoring Weights ====================


@router.get("/scoring/weights", response_model=ScoringWeightsResponse)
async def get_scoring_weights():
    """Get current scoring engine weights."""
    weights = ScoringWeightsConfig(**_scoring_weights)
    total = sum(_scoring_weights.values())
    return ScoringWeightsResponse(
        weights=weights,
        total=round(total, 4),
        is_valid=abs(total - 1.0) < 0.001,
        message="Weights are valid" if abs(total - 1.0) < 0.001 else "Weights do not sum to 1.0",
    )


@router.put("/scoring/weights", response_model=ScoringWeightsResponse)
async def update_scoring_weights(weights: ScoringWeightsConfig):
    """Update scoring engine weights."""
    weight_dict = weights.model_dump()
    total = sum(weight_dict.values())

    if abs(total - 1.0) > 0.001:
        raise HTTPException(
            status_code=400,
            detail=f"Weights must sum to 1.0, got {total:.4f}",
        )

    _scoring_weights.update(weight_dict)
    logger.info("admin.scoring.weights_updated", weights=weight_dict)

    return ScoringWeightsResponse(
        weights=weights,
        total=round(total, 4),
        is_valid=True,
        message="Scoring weights updated successfully",
    )


# ==================== Alert Configuration ====================


@router.get("/alerts/config", response_model=AlertConfigResponse)
async def get_alert_config():
    """Get current alert configuration."""
    from app.core.config import settings

    chat_id = settings.telegram_chat_id
    return AlertConfigResponse(
        telegram_configured=bool(settings.telegram_bot_token and settings.telegram_chat_id),
        telegram_chat_id_masked=f"***{chat_id[-4:]}" if chat_id and len(chat_id) > 4 else None,
        min_score_for_alert=_alert_config["min_score_for_alert"],
        score_change_threshold=_alert_config["score_change_threshold"],
        alert_cooldown_hours=_alert_config["alert_cooldown_hours"],
        max_alerts_per_cycle=_alert_config["max_alerts_per_cycle"],
        alerts_enabled=_alert_config["alerts_enabled"],
    )


@router.put("/alerts/config", response_model=AlertConfigResponse)
async def update_alert_config(data: AlertConfigUpdate):
    """Update alert configuration."""
    update_data = data.model_dump(exclude_unset=True)

    # Handle telegram settings separately (env-level)
    telegram_fields = {"telegram_bot_token", "telegram_chat_id"}
    config_fields = {k: v for k, v in update_data.items() if k not in telegram_fields}

    for key, value in config_fields.items():
        if key in _alert_config:
            _alert_config[key] = value

    logger.info("admin.alerts.config_updated", fields=list(config_fields.keys()))
    return await get_alert_config()


@router.get("/alerts/history")
async def get_alert_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    alert_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get alert history with pagination."""
    query = select(AlertLog).order_by(AlertLog.created_at.desc())

    if alert_type:
        query = query.where(AlertLog.alert_type == alert_type)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    alerts = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "alerts": [
            {
                "id": str(a.id),
                "project_id": str(a.project_id),
                "alert_type": a.alert_type,
                "channel": a.channel,
                "priority": a.priority,
                "title": a.title,
                "delivered": a.delivered,
                "sent_at": a.sent_at.isoformat() if a.sent_at else None,
                "created_at": a.created_at.isoformat(),
            }
            for a in alerts
        ],
    }


# ==================== System Monitoring ====================


@router.get("/system/status", response_model=SystemStatusResponse)
async def get_system_status(db: AsyncSession = Depends(get_db)):
    """Get comprehensive system status."""
    from app.core.redis import redis_client

    # Database check
    try:
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"

    # Redis check
    try:
        await redis_client.ping()
        redis_status = "connected"
    except Exception as e:
        redis_status = f"error: {e}"

    # Celery check
    try:
        from app.tasks.celery_app import celery_app
        inspector = celery_app.control.inspect()
        active = inspector.active()
        celery_status = "connected" if active is not None else "no workers"
    except Exception:
        celery_status = "unavailable"

    # Collector statuses
    collector_configs = [
        {"name": "dexscreener", "rpm": 60, "type": "market"},
        {"name": "coingecko", "rpm": 10, "type": "market"},
        {"name": "geckoterminal", "rpm": 10, "type": "market"},
        {"name": "defillama", "rpm": 30, "type": "defi"},
        {"name": "goplus", "rpm": 30, "type": "security"},
        {"name": "reddit", "rpm": 10, "type": "social"},
        {"name": "etherscan", "rpm": 5, "type": "onchain"},
        {"name": "twitter", "rpm": 15, "type": "social"},
        {"name": "coinmarketcap", "rpm": 10, "type": "market"},
    ]

    # Fetch data source statuses from DB
    ds_result = await db.execute(select(DataSource))
    db_sources = {s.name: s for s in ds_result.scalars().all()}

    collectors = []
    for cfg in collector_configs:
        db_src = db_sources.get(cfg["name"])
        from app.core.config import settings
        is_configured = True
        if cfg["name"] == "etherscan":
            is_configured = bool(settings.etherscan_api_key)
        elif cfg["name"] == "twitter":
            is_configured = False  # needs TWITTER_BEARER_TOKEN
        elif cfg["name"] == "coinmarketcap":
            is_configured = False  # needs CMC_API_KEY

        collectors.append({
            "name": cfg["name"],
            "is_active": db_src.is_active if db_src else True,
            "is_configured": is_configured,
            "last_success": db_src.last_success if db_src else None,
            "last_error": db_src.last_error if db_src else None,
            "error_count": db_src.error_count if db_src else 0,
            "rate_limit_rpm": cfg["rpm"],
            "rate_limit_rpd": None,
        })

    # Stats
    total_projects = (await db.execute(select(func.count(Project.id)))).scalar() or 0
    active_projects = (await db.execute(
        select(func.count(Project.id)).where(Project.is_active.is_(True))
    )).scalar() or 0
    total_scores = (await db.execute(select(func.count(ProjectScore.id)))).scalar() or 0
    total_alerts = (await db.execute(select(func.count(AlertLog.id)))).scalar() or 0
    total_red_flags = (await db.execute(select(func.count(RedFlag.id)))).scalar() or 0
    total_ai_reports = (await db.execute(select(func.count(AIReport.id)))).scalar() or 0

    return SystemStatusResponse(
        database=db_status,
        redis=redis_status,
        celery=celery_status,
        collectors=collectors,
        total_projects=total_projects,
        active_projects=active_projects,
        total_scores=total_scores,
        total_alerts=total_alerts,
        total_red_flags=total_red_flags,
        total_ai_reports=total_ai_reports,
        uptime="N/A",
    )


@router.post("/tasks/trigger", response_model=TaskTriggerResponse)
async def trigger_task(data: TaskTriggerRequest):
    """Manually trigger a background task."""
    task_map = {
        "scan_new_projects": "app.tasks.collector_tasks.scan_new_projects",
        "collect_market_data": "app.tasks.collector_tasks.collect_market_data",
        "collect_social_data": "app.tasks.collector_tasks.collect_social_data",
        "collect_onchain_data": "app.tasks.collector_tasks.collect_onchain_data",
        "calculate_all_scores": "app.tasks.scoring_tasks.calculate_all_scores",
        "run_ai_analysis": "app.tasks.scoring_tasks.run_ai_analysis",
        "send_alerts": "app.tasks.alert_tasks.send_alerts",
        "send_daily_summary": "app.tasks.alert_tasks.send_daily_summary",
        "cleanup_old_data": "app.tasks.collector_tasks.cleanup_old_data",
    }

    task_path = task_map.get(data.task_name)
    if not task_path:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown task '{data.task_name}'. Available: {list(task_map.keys())}",
        )

    from app.tasks.celery_app import celery_app
    result = celery_app.send_task(task_path)

    logger.info("admin.task.triggered", task_name=data.task_name, task_id=result.id)
    return TaskTriggerResponse(
        task_id=result.id,
        task_name=data.task_name,
        status="queued",
        message=f"Task '{data.task_name}' triggered successfully",
    )


@router.get("/tasks/schedule")
async def get_task_schedule():
    """Get the current Celery beat schedule."""
    from app.tasks.celery_app import celery_app

    schedule = celery_app.conf.beat_schedule
    tasks = []
    for name, config in schedule.items():
        tasks.append({
            "name": name,
            "task": config["task"],
            "schedule": str(config["schedule"]),
        })
    return {"tasks": tasks}


# ==================== AI Reports ====================


@router.get("/ai-reports", response_model=list[AIReportResponse])
async def list_ai_reports(
    project_id: uuid.UUID | None = None,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List AI analysis reports."""
    query = select(AIReport).order_by(AIReport.created_at.desc())
    if project_id:
        query = query.where(AIReport.project_id == project_id)
    query = query.limit(limit)

    result = await db.execute(query)
    reports = result.scalars().all()
    return [AIReportResponse.model_validate(r) for r in reports]


@router.get("/ai-reports/{report_id}", response_model=AIReportResponse)
async def get_ai_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific AI report with full details."""
    result = await db.execute(select(AIReport).where(AIReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="AI report not found")
    return AIReportResponse.model_validate(report)


# ==================== Watchlist ====================


@router.get("/watchlist/{user_id}", response_model=list[WatchlistResponse])
async def get_watchlist(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a user's watchlist."""
    result = await db.execute(
        select(UserWatchlist)
        .where(UserWatchlist.user_id == user_id)
        .order_by(UserWatchlist.created_at.desc())
    )
    items = result.scalars().all()
    return [WatchlistResponse.model_validate(w) for w in items]


@router.post("/watchlist/{user_id}", response_model=WatchlistResponse, status_code=201)
async def add_to_watchlist(
    user_id: str,
    data: WatchlistAdd,
    db: AsyncSession = Depends(get_db),
):
    """Add a project to a user's watchlist."""
    # Check project exists
    project = await db.execute(select(Project).where(Project.id == data.project_id))
    if not project.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    # Check duplicate
    existing = await db.execute(
        select(UserWatchlist).where(
            UserWatchlist.user_id == user_id,
            UserWatchlist.project_id == data.project_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Project already in watchlist")

    item = UserWatchlist(
        user_id=user_id,
        project_id=data.project_id,
        alert_enabled=data.alert_enabled,
        min_score_alert=data.min_score_alert,
        notes=data.notes,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    logger.info("admin.watchlist.added", user_id=user_id, project_id=str(data.project_id))
    return WatchlistResponse.model_validate(item)


@router.put("/watchlist/{user_id}/{project_id}", response_model=WatchlistResponse)
async def update_watchlist_item(
    user_id: str,
    project_id: uuid.UUID,
    data: WatchlistUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a watchlist item."""
    result = await db.execute(
        select(UserWatchlist).where(
            UserWatchlist.user_id == user_id,
            UserWatchlist.project_id == project_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    await db.flush()
    await db.refresh(item)
    return WatchlistResponse.model_validate(item)


@router.delete("/watchlist/{user_id}/{project_id}")
async def remove_from_watchlist(
    user_id: str,
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Remove a project from watchlist."""
    result = await db.execute(
        select(UserWatchlist).where(
            UserWatchlist.user_id == user_id,
            UserWatchlist.project_id == project_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    await db.delete(item)
    logger.info("admin.watchlist.removed", user_id=user_id, project_id=str(project_id))
    return {"message": "Removed from watchlist"}


# ==================== Cleanup Configuration ====================


@router.get("/cleanup/config", response_model=CleanupConfigResponse)
async def get_cleanup_config():
    """Get current data cleanup configuration."""
    return CleanupConfigResponse(**_cleanup_config)


@router.put("/cleanup/config", response_model=CleanupConfigResponse)
async def update_cleanup_config(
    market_data_retention_days: int | None = Query(None, ge=7, le=365),
    social_data_retention_days: int | None = Query(None, ge=7, le=365),
    score_history_retention_days: int | None = Query(None, ge=7, le=730),
    inactive_project_archive_days: int | None = Query(None, ge=7, le=365),
):
    """Update data cleanup configuration."""
    if market_data_retention_days is not None:
        _cleanup_config["market_data_retention_days"] = market_data_retention_days
    if social_data_retention_days is not None:
        _cleanup_config["social_data_retention_days"] = social_data_retention_days
    if score_history_retention_days is not None:
        _cleanup_config["score_history_retention_days"] = score_history_retention_days
    if inactive_project_archive_days is not None:
        _cleanup_config["inactive_project_archive_days"] = inactive_project_archive_days

    logger.info("admin.cleanup.config_updated", config=_cleanup_config)
    return CleanupConfigResponse(**_cleanup_config)


@router.post("/cleanup/run")
async def trigger_cleanup(db: AsyncSession = Depends(get_db)):
    """Manually trigger data cleanup."""
    from app.tasks.collector_tasks import cleanup_old_data
    task = cleanup_old_data.delay()
    return {
        "task_id": task.id,
        "message": "Cleanup task triggered",
    }


# ==================== Database Stats ====================


@router.get("/stats/database")
async def get_database_stats(db: AsyncSession = Depends(get_db)):
    """Get database table statistics."""
    from sqlalchemy import text

    tables = [
        "projects", "project_scores", "market_data", "social_data",
        "score_history", "onchain_data", "whale_activities",
        "red_flags", "ai_reports", "alerts_log", "user_watchlist",
        "data_sources", "token_launches",
    ]

    stats = []
    for table in tables:
        try:
            result = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))  # noqa: S608
            count = result.scalar() or 0
            stats.append({"table": table, "rows": count})
        except Exception:
            stats.append({"table": table, "rows": -1, "error": "table not found"})

    return {"tables": stats}


@router.get("/stats/storage")
async def get_storage_stats(db: AsyncSession = Depends(get_db)):
    """Get storage usage statistics."""
    from sqlalchemy import text

    try:
        result = await db.execute(text(
            "SELECT pg_size_pretty(pg_database_size(current_database())) as db_size"
        ))
        row = result.fetchone()
        db_size = row[0] if row else "unknown"
    except Exception:
        db_size = "unknown"

    # Get time-series data ranges
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)

    market_24h = (await db.execute(
        select(func.count()).select_from(MarketData).where(MarketData.time >= day_ago)
    )).scalar() or 0
    market_7d = (await db.execute(
        select(func.count()).select_from(MarketData).where(MarketData.time >= week_ago)
    )).scalar() or 0

    return {
        "database_size": db_size,
        "market_data_24h": market_24h,
        "market_data_7d": market_7d,
    }
