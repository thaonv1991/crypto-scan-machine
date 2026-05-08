import uuid
from datetime import datetime

from pydantic import BaseModel, Field

# --- Project Management ---


class ProjectUpdate(BaseModel):
    name: str | None = None
    symbol: str | None = None
    contract_address: str | None = None
    blockchain: str | None = None
    website: str | None = None
    description: str | None = None
    category: str | None = None
    twitter_url: str | None = None
    telegram_url: str | None = None
    discord_url: str | None = None
    github_url: str | None = None
    status: str | None = None
    is_active: bool | None = None


class BulkStatusUpdate(BaseModel):
    project_ids: list[uuid.UUID]
    status: str
    is_active: bool | None = None


class BulkActionResponse(BaseModel):
    updated: int
    message: str


# --- Data Source / API Key Management ---


class DataSourceCreate(BaseModel):
    name: str
    source_type: str
    base_url: str | None = None
    rate_limit_per_minute: int = 30
    rate_limit_per_day: int | None = None
    is_active: bool = True
    config: dict | None = None


class DataSourceUpdate(BaseModel):
    name: str | None = None
    source_type: str | None = None
    base_url: str | None = None
    rate_limit_per_minute: int | None = None
    rate_limit_per_day: int | None = None
    is_active: bool | None = None
    config: dict | None = None


class DataSourceResponse(BaseModel):
    id: uuid.UUID
    name: str
    source_type: str
    base_url: str | None = None
    rate_limit_per_minute: int
    rate_limit_per_day: int | None = None
    current_usage_minute: int
    current_usage_day: int
    is_active: bool
    last_success: datetime | None = None
    last_error: str | None = None
    error_count: int
    consecutive_errors: int
    config: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DataSourceListResponse(BaseModel):
    total: int
    sources: list[DataSourceResponse]


# --- Scoring Weights ---


class ScoringWeightsConfig(BaseModel):
    engine1_weight: float = Field(0.15, ge=0, le=1, description="Discovery engine weight")
    engine2_weight: float = Field(0.30, ge=0, le=1, description="Market engine weight")
    engine3_weight: float = Field(0.15, ge=0, le=1, description="Social engine weight")
    engine4_weight: float = Field(0.25, ge=0, le=1, description="Security engine weight")
    engine5_weight: float = Field(0.15, ge=0, le=1, description="AI engine weight")


class ScoringWeightsResponse(BaseModel):
    weights: ScoringWeightsConfig
    total: float
    is_valid: bool
    message: str


# --- Alert Configuration ---


class AlertConfigUpdate(BaseModel):
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    min_score_for_alert: float | None = Field(None, ge=0, le=100)
    score_change_threshold: float | None = Field(None, ge=0, le=100)
    alert_cooldown_hours: int | None = Field(None, ge=1, le=72)
    max_alerts_per_cycle: int | None = Field(None, ge=1, le=100)
    alerts_enabled: bool | None = None


class AlertConfigResponse(BaseModel):
    telegram_configured: bool
    telegram_chat_id_masked: str | None = None
    min_score_for_alert: float
    score_change_threshold: float
    alert_cooldown_hours: int
    max_alerts_per_cycle: int
    alerts_enabled: bool


# --- System Monitoring ---


class TaskTriggerRequest(BaseModel):
    task_name: str


class TaskTriggerResponse(BaseModel):
    task_id: str
    task_name: str
    status: str
    message: str


class CollectorStatusResponse(BaseModel):
    name: str
    is_active: bool
    is_configured: bool
    last_success: datetime | None = None
    last_error: str | None = None
    error_count: int
    rate_limit_rpm: int
    rate_limit_rpd: int | None = None


class SystemStatusResponse(BaseModel):
    database: str
    redis: str
    celery: str
    collectors: list[CollectorStatusResponse]
    total_projects: int
    active_projects: int
    total_scores: int
    total_alerts: int
    total_red_flags: int
    total_ai_reports: int
    uptime: str


# --- Cleanup ---


class CleanupConfigResponse(BaseModel):
    market_data_retention_days: int
    social_data_retention_days: int
    score_history_retention_days: int
    inactive_project_archive_days: int
    last_cleanup: datetime | None = None


class CleanupResultResponse(BaseModel):
    market_data_deleted: int
    social_data_deleted: int
    score_history_deleted: int
    projects_archived: int
    cold_storage_bytes: int
    duration_seconds: float


# --- AI Reports ---


class AIReportResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    report_type: str
    ai_model: str
    summary: str | None = None
    recommendation: str | None = None
    ai_score: float | None = None
    confidence: float | None = None
    cost_usd: float | None = None
    structured_data: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Watchlist ---


class WatchlistAdd(BaseModel):
    project_id: uuid.UUID
    alert_enabled: bool = True
    min_score_alert: float = 70.0
    notes: str | None = None


class WatchlistUpdate(BaseModel):
    alert_enabled: bool | None = None
    min_score_alert: float | None = None
    notes: str | None = None


class WatchlistResponse(BaseModel):
    id: uuid.UUID
    user_id: str
    project_id: uuid.UUID
    alert_enabled: bool
    min_score_alert: float
    notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
