from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.project import Project


class MarketData(Base):
    """Time-series market data - will be converted to TimescaleDB hypertable."""

    __tablename__ = "market_data"

    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, server_default=func.now()
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )

    # Price data
    price_usd: Mapped[float | None] = mapped_column(Float)
    price_btc: Mapped[float | None] = mapped_column(Float)
    price_eth: Mapped[float | None] = mapped_column(Float)

    # Volume
    volume_24h: Mapped[float | None] = mapped_column(Float)
    volume_change_pct: Mapped[float | None] = mapped_column(Float)

    # Market cap
    market_cap: Mapped[float | None] = mapped_column(Float)
    fdv: Mapped[float | None] = mapped_column(Float)

    # Liquidity
    liquidity_usd: Mapped[float | None] = mapped_column(Float)
    liquidity_score: Mapped[float | None] = mapped_column(Float)

    # Price changes
    price_change_1h: Mapped[float | None] = mapped_column(Float)
    price_change_24h: Mapped[float | None] = mapped_column(Float)
    price_change_7d: Mapped[float | None] = mapped_column(Float)

    # Trading info
    buy_count: Mapped[int | None] = mapped_column(Integer)
    sell_count: Mapped[int | None] = mapped_column(Integer)
    holders_count: Mapped[int | None] = mapped_column(Integer)

    # Source
    source: Mapped[str] = mapped_column(String(50), default="coingecko")
    extra_data: Mapped[dict | None] = mapped_column(JSONB)

    # Relationship
    project: Mapped[Project] = relationship(back_populates="market_data")

    __table_args__ = (
        Index("ix_market_data_project_time", "project_id", "time"),
    )


class SocialData(Base):
    """Time-series social data - will be converted to TimescaleDB hypertable."""

    __tablename__ = "social_data"

    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, server_default=func.now()
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )

    # Twitter metrics
    twitter_followers: Mapped[int | None] = mapped_column(Integer)
    twitter_following: Mapped[int | None] = mapped_column(Integer)
    twitter_tweets_count: Mapped[int | None] = mapped_column(Integer)
    twitter_engagement_rate: Mapped[float | None] = mapped_column(Float)
    twitter_mentions_count: Mapped[int | None] = mapped_column(Integer)

    # Telegram metrics
    telegram_members: Mapped[int | None] = mapped_column(Integer)
    telegram_online: Mapped[int | None] = mapped_column(Integer)
    telegram_messages_24h: Mapped[int | None] = mapped_column(Integer)

    # Reddit metrics
    reddit_subscribers: Mapped[int | None] = mapped_column(Integer)
    reddit_active_users: Mapped[int | None] = mapped_column(Integer)
    reddit_posts_24h: Mapped[int | None] = mapped_column(Integer)

    # Sentiment
    sentiment_score: Mapped[float | None] = mapped_column(Float)
    sentiment_label: Mapped[str | None] = mapped_column(String(20))

    # Source
    source: Mapped[str] = mapped_column(String(50), default="twitter")
    extra_data: Mapped[dict | None] = mapped_column(JSONB)

    # Relationship
    project: Mapped[Project] = relationship(back_populates="social_data")

    __table_args__ = (
        Index("ix_social_data_project_time", "project_id", "time"),
    )


class ScoreHistory(Base):
    """Time-series score history - will be converted to TimescaleDB hypertable."""

    __tablename__ = "score_history"

    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, server_default=func.now()
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )

    # Scores
    engine1_score: Mapped[float] = mapped_column(Float, default=0.0)
    engine2_score: Mapped[float] = mapped_column(Float, default=0.0)
    engine3_score: Mapped[float] = mapped_column(Float, default=0.0)
    engine4_score: Mapped[float] = mapped_column(Float, default=0.0)
    engine5_score: Mapped[float] = mapped_column(Float, default=0.0)
    total_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Delta from previous
    score_delta: Mapped[float | None] = mapped_column(Float)
    red_flag_count: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        Index("ix_score_history_project_time", "project_id", "time"),
        Index("ix_score_history_total", "total_score"),
    )
