from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import redis_client
from app.schemas.project import HealthResponse

router = APIRouter(tags=["health"])
logger = structlog.get_logger()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    db_status = "unknown"
    redis_status = "unknown"

    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"
        logger.error("health.db_error", error=str(e))

    try:
        await redis_client.ping()
        redis_status = "connected"
    except Exception as e:
        redis_status = f"error: {e}"
        logger.error("health.redis_error", error=str(e))

    status = "healthy" if db_status == "connected" and redis_status == "connected" else "degraded"

    return HealthResponse(
        status=status,
        database=db_status,
        redis=redis_status,
        timestamp=datetime.now(timezone.utc),
    )
