import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class RedFlag(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "red_flags"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Flag info
    flag_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Detection
    detected_by: Mapped[str] = mapped_column(String(100), nullable=False)
    engine: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Evidence
    evidence: Mapped[dict | None] = mapped_column(JSONB)

    # Relationship
    project: Mapped["Project"] = relationship(back_populates="red_flags")  # noqa: F821

    __table_args__ = (
        Index("ix_red_flags_project_active", "project_id", "is_active"),
        Index("ix_red_flags_severity", "severity"),
        Index("ix_red_flags_type", "flag_type"),
    )


class AIReport(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "ai_reports"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Report info
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    ai_model: Mapped[str] = mapped_column(String(100), nullable=False)

    # Content
    summary: Mapped[str | None] = mapped_column(Text)
    full_report: Mapped[str | None] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(String(50))

    # Scores from AI
    ai_score: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[float | None] = mapped_column(Float)

    # Token usage
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[float | None] = mapped_column(Float)

    # Structured output
    structured_data: Mapped[dict | None] = mapped_column(JSONB)

    __table_args__ = (
        Index("ix_ai_reports_project_type", "project_id", "report_type"),
        Index("ix_ai_reports_model", "ai_model"),
    )


class AlertLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "alerts_log"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Alert info
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="medium")

    # Content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)

    # Delivery
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[str | None] = mapped_column(Text)

    # Reference data
    score_at_alert: Mapped[float | None] = mapped_column(Float)
    trigger_data: Mapped[dict | None] = mapped_column(JSONB)

    __table_args__ = (
        Index("ix_alerts_log_project_type", "project_id", "alert_type"),
        Index("ix_alerts_log_channel", "channel"),
        Index("ix_alerts_log_sent", "sent_at"),
    )


class UserWatchlist(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "user_watchlist"

    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Settings
    alert_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    min_score_alert: Mapped[float] = mapped_column(Float, default=70.0)
    notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("ix_watchlist_user_project", "user_id", "project_id", unique=True),
    )


class DataSource(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "data_sources"

    # Source info
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(500))

    # Rate limiting
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=30)
    rate_limit_per_day: Mapped[int | None] = mapped_column(Integer)
    current_usage_minute: Mapped[int] = mapped_column(Integer, default=0)
    current_usage_day: Mapped[int] = mapped_column(Integer, default=0)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_success: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    consecutive_errors: Mapped[int] = mapped_column(Integer, default=0)

    # Config
    config: Mapped[dict | None] = mapped_column(JSONB)

    __table_args__ = (
        Index("ix_data_sources_type", "source_type"),
        Index("ix_data_sources_active", "is_active"),
    )
