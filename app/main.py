from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.health import router as health_router
from app.api.projects import router as projects_router
from app.api.auth import router as auth_router
from app.api.ws import router as ws_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.redis import redis_client

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    logger.info("app.starting", env=settings.app_env)

    # Verify redis connection
    try:
        await redis_client.ping()
        logger.info("redis.connected")
    except Exception as e:
        logger.error("redis.connection_failed", error=str(e))

    yield

    # Cleanup
    await redis_client.aclose()
    logger.info("app.shutdown")


app = FastAPI(
    title=settings.app_name,
    description="24/7 cryptocurrency scanning and scoring system",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi import Depends
from app.core.security import verify_api_key

# Routers - Locked behind VIP API Key
app.include_router(health_router) # Health is public
app.include_router(auth_router) # Auth is public (Registration/Login)
app.include_router(ws_router, prefix="/api/ws") # WebSocket is public/session-based
app.include_router(projects_router, dependencies=[Depends(verify_api_key)])
app.include_router(admin_router, dependencies=[Depends(verify_api_key)])


@app.get("/")
async def root():
    return {
        "app": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
    }
