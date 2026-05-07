import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ProjectBase(BaseModel):
    name: str
    symbol: str | None = None
    slug: str
    contract_address: str | None = None
    blockchain: str = "ethereum"
    website: str | None = None
    description: str | None = None
    category: str | None = None
    twitter_url: str | None = None
    telegram_url: str | None = None
    discord_url: str | None = None
    source: str


class ProjectCreate(ProjectBase):
    pass


class ProjectResponse(ProjectBase):
    id: uuid.UUID
    status: str
    is_active: bool
    discovered_at: datetime
    created_at: datetime
    updated_at: datetime
    extra_data: dict | None = None

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    total: int
    page: int
    per_page: int
    projects: list[ProjectResponse]


class ProjectScoreResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    engine1_score: float
    engine2_score: float
    engine3_score: float
    engine4_score: float
    engine5_score: float
    total_score: float
    red_flag_count: int
    has_critical_flag: bool
    score_breakdown: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectDetailResponse(ProjectResponse):
    scores: list[ProjectScoreResponse] = []


class TokenLaunchResponse(BaseModel):
    id: uuid.UUID
    launchpad: str
    token_name: str
    token_symbol: str | None = None
    blockchain: str
    raise_amount: float | None = None
    token_price: float | None = None
    fdv: float | None = None
    sale_start: datetime | None = None
    sale_end: datetime | None = None
    tge_date: datetime | None = None
    status: str
    source_url: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MarketDataResponse(BaseModel):
    time: datetime
    price_usd: float | None = None
    volume_24h: float | None = None
    market_cap: float | None = None
    liquidity_usd: float | None = None
    price_change_24h: float | None = None
    holders_count: int | None = None
    source: str

    model_config = {"from_attributes": True}


class RedFlagResponse(BaseModel):
    id: uuid.UUID
    flag_type: str
    severity: str
    title: str
    description: str | None = None
    detected_by: str
    engine: str
    confidence: float
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    alert_type: str
    channel: str
    priority: str
    title: str
    message: str | None = None
    delivered: bool
    sent_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class HealthResponse(BaseModel):
    status: str
    version: str = "0.1.0"
    database: str = "unknown"
    redis: str = "unknown"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DashboardStats(BaseModel):
    total_projects: int = 0
    active_projects: int = 0
    new_projects_24h: int = 0
    avg_score: float = 0.0
    top_score: float = 0.0
    alerts_sent_24h: int = 0
    red_flags_active: int = 0
