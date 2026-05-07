import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if True:  # TYPE_CHECKING workaround for circular imports
    from app.models.analysis import RedFlag  # noqa: F401
    from app.models.onchain import OnchainData  # noqa: F401
    from app.models.timeseries import MarketData, SocialData  # noqa: F401


class ProjectStatus(str, PyEnum):
    NEW = "new"
    MONITORING = "monitoring"
    ALERT_SENT = "alert_sent"
    ARCHIVED = "archived"
    BLACKLISTED = "blacklisted"


class BlockchainNetwork(str, PyEnum):
    ETHEREUM = "ethereum"
    BSC = "bsc"
    SOLANA = "solana"
    BASE = "base"
    ARBITRUM = "arbitrum"
    POLYGON = "polygon"
    AVALANCHE = "avalanche"
    OTHER = "other"


class Project(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(50))
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    # Contract & chain info
    contract_address: Mapped[str | None] = mapped_column(String(255))
    blockchain: Mapped[str] = mapped_column(String(50), default=BlockchainNetwork.ETHEREUM.value)
    pair_address: Mapped[str | None] = mapped_column(String(255))

    # Project info
    website: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    category: Mapped[str | None] = mapped_column(String(100))

    # Social links
    twitter_url: Mapped[str | None] = mapped_column(String(500))
    telegram_url: Mapped[str | None] = mapped_column(String(500))
    discord_url: Mapped[str | None] = mapped_column(String(500))
    github_url: Mapped[str | None] = mapped_column(String(500))

    # Discovery info
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    launch_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Status
    status: Mapped[str] = mapped_column(String(50), default=ProjectStatus.NEW.value)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Metadata
    extra_data: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    # Relationships
    scores: Mapped[list["ProjectScore"]] = relationship(back_populates="project", lazy="selectin")
    market_data: Mapped[list["MarketData"]] = relationship(back_populates="project", lazy="noload")
    social_data: Mapped[list["SocialData"]] = relationship(back_populates="project", lazy="noload")
    onchain_data: Mapped[list["OnchainData"]] = relationship(back_populates="project", lazy="noload")
    red_flags: Mapped[list["RedFlag"]] = relationship(back_populates="project", lazy="selectin")

    __table_args__ = (
        Index("ix_projects_status", "status"),
        Index("ix_projects_blockchain", "blockchain"),
        Index("ix_projects_source", "source"),
        Index("ix_projects_discovered_at", "discovered_at"),
        Index("ix_projects_is_active", "is_active"),
        Index("ix_projects_contract_address", "contract_address"),
        Index("ix_projects_name_trgm", "name", postgresql_using="gin", postgresql_ops={"name": "gin_trgm_ops"}),
    )

    def __repr__(self) -> str:
        return f"<Project {self.name} ({self.symbol})>"


class ProjectScore(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "project_scores"

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    # Individual engine scores (0-100)
    engine1_score: Mapped[float] = mapped_column(Float, default=0.0)
    engine2_score: Mapped[float] = mapped_column(Float, default=0.0)
    engine3_score: Mapped[float] = mapped_column(Float, default=0.0)
    engine4_score: Mapped[float] = mapped_column(Float, default=0.0)
    engine5_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Composite score
    total_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Weights used
    weights: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    # Score details
    score_breakdown: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    # Red flag count
    red_flag_count: Mapped[int] = mapped_column(Integer, default=0)
    has_critical_flag: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationship
    project: Mapped["Project"] = relationship(back_populates="scores")

    __table_args__ = (
        Index("ix_project_scores_total", "total_score"),
        Index("ix_project_scores_project_created", "project_id", "created_at"),
    )


class TokenLaunch(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "token_launches"

    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)

    # Launch info
    launchpad: Mapped[str] = mapped_column(String(100), nullable=False)
    token_name: Mapped[str] = mapped_column(String(255), nullable=False)
    token_symbol: Mapped[str | None] = mapped_column(String(50))
    blockchain: Mapped[str] = mapped_column(String(50), nullable=False)

    # Financial info
    raise_amount: Mapped[float | None] = mapped_column(Float)
    token_price: Mapped[float | None] = mapped_column(Float)
    fdv: Mapped[float | None] = mapped_column(Float)
    initial_market_cap: Mapped[float | None] = mapped_column(Float)

    # Dates
    sale_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sale_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tge_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Status
    status: Mapped[str] = mapped_column(String(50), default="upcoming")
    source_url: Mapped[str | None] = mapped_column(String(500))

    # Metadata
    extra_data: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    __table_args__ = (
        Index("ix_token_launches_launchpad", "launchpad"),
        Index("ix_token_launches_blockchain", "blockchain"),
        Index("ix_token_launches_tge_date", "tge_date"),
        Index("ix_token_launches_status", "status"),
    )
