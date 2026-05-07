import uuid
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.analysis import AlertLog, RedFlag
from app.models.project import Project, ProjectScore
from app.models.timeseries import MarketData
from app.schemas.project import (
    DashboardStats,
    MarketDataResponse,
    ProjectCreate,
    ProjectDetailResponse,
    ProjectListResponse,
    ProjectResponse,
    ProjectScoreResponse,
    RedFlagResponse,
)

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])
logger = structlog.get_logger()


@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = None,
    blockchain: str | None = None,
    min_score: float | None = None,
    sort_by: str = "discovered_at",
    order: str = "desc",
    db: AsyncSession = Depends(get_db),
):
    query = select(Project).where(Project.is_active.is_(True))

    if status:
        query = query.where(Project.status == status)
    if blockchain:
        query = query.where(Project.blockchain == blockchain)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Sort
    if sort_by == "discovered_at":
        sort_col = Project.discovered_at
    elif sort_by == "name":
        sort_col = Project.name
    else:
        sort_col = Project.discovered_at

    if order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    # Paginate
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    projects = result.scalars().all()

    return ProjectListResponse(
        total=total,
        page=page,
        per_page=per_page,
        projects=[ProjectResponse.model_validate(p) for p in projects],
    )


@router.get("/top", response_model=list[ProjectDetailResponse])
async def get_top_projects(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get top projects by score."""
    query = (
        select(Project)
        .where(Project.is_active.is_(True))
        .order_by(Project.discovered_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    projects = result.scalars().all()
    return [ProjectDetailResponse.model_validate(p) for p in projects]


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Get dashboard statistics."""
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)

    total = (await db.execute(select(func.count(Project.id)))).scalar() or 0
    active = (
        await db.execute(select(func.count(Project.id)).where(Project.is_active.is_(True)))
    ).scalar() or 0
    new_24h = (
        await db.execute(
            select(func.count(Project.id)).where(Project.discovered_at >= day_ago)
        )
    ).scalar() or 0

    avg_score_result = (
        await db.execute(select(func.avg(ProjectScore.total_score)))
    ).scalar()
    top_score_result = (
        await db.execute(select(func.max(ProjectScore.total_score)))
    ).scalar()

    alerts_24h = (
        await db.execute(
            select(func.count(AlertLog.id)).where(AlertLog.sent_at >= day_ago)
        )
    ).scalar() or 0

    red_flags_active = (
        await db.execute(
            select(func.count(RedFlag.id)).where(RedFlag.is_active.is_(True))
        )
    ).scalar() or 0

    return DashboardStats(
        total_projects=total,
        active_projects=active,
        new_projects_24h=new_24h,
        avg_score=round(avg_score_result or 0.0, 2),
        top_score=round(top_score_result or 0.0, 2),
        alerts_sent_24h=alerts_24h,
        red_flags_active=red_flags_active,
    )


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectDetailResponse.model_validate(project)


@router.get("/{project_id}/scores", response_model=list[ProjectScoreResponse])
async def get_project_scores(
    project_id: uuid.UUID,
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ProjectScore)
        .where(ProjectScore.project_id == project_id)
        .order_by(ProjectScore.created_at.desc())
        .limit(limit)
    )
    scores = result.scalars().all()
    return [ProjectScoreResponse.model_validate(s) for s in scores]


@router.get("/{project_id}/market-data", response_model=list[MarketDataResponse])
async def get_project_market_data(
    project_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MarketData)
        .where(MarketData.project_id == project_id)
        .order_by(MarketData.time.desc())
        .limit(limit)
    )
    data = result.scalars().all()
    return [MarketDataResponse.model_validate(d) for d in data]


@router.get("/{project_id}/red-flags", response_model=list[RedFlagResponse])
async def get_project_red_flags(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RedFlag)
        .where(RedFlag.project_id == project_id)
        .order_by(RedFlag.created_at.desc())
    )
    flags = result.scalars().all()
    return [RedFlagResponse.model_validate(f) for f in flags]


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
):
    """Manually add a project to track."""
    existing = await db.execute(
        select(Project).where(Project.slug == project_data.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Project with this slug already exists")

    project = Project(**project_data.model_dump())
    db.add(project)
    await db.flush()
    await db.refresh(project)
    logger.info("project.created", project_id=str(project.id), name=project.name)
    return ProjectResponse.model_validate(project)
