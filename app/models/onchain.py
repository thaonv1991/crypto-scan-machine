from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.project import Project


class OnchainData(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "onchain_data"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Token info
    total_supply: Mapped[float | None] = mapped_column(Float)
    circulating_supply: Mapped[float | None] = mapped_column(Float)
    burn_amount: Mapped[float | None] = mapped_column(Float)

    # Holders
    holder_count: Mapped[int | None] = mapped_column(Integer)
    top10_holder_pct: Mapped[float | None] = mapped_column(Float)
    top50_holder_pct: Mapped[float | None] = mapped_column(Float)

    # Contract
    is_verified: Mapped[bool | None] = mapped_column(Boolean)
    is_renounced: Mapped[bool | None] = mapped_column(Boolean)
    has_proxy: Mapped[bool | None] = mapped_column(Boolean)
    has_mint_function: Mapped[bool | None] = mapped_column(Boolean)
    has_blacklist: Mapped[bool | None] = mapped_column(Boolean)
    buy_tax: Mapped[float | None] = mapped_column(Float)
    sell_tax: Mapped[float | None] = mapped_column(Float)

    # Liquidity
    liquidity_locked: Mapped[bool | None] = mapped_column(Boolean)
    liquidity_lock_duration: Mapped[int | None] = mapped_column(Integer)
    lp_burned_pct: Mapped[float | None] = mapped_column(Float)

    # Activity
    tx_count_24h: Mapped[int | None] = mapped_column(Integer)
    unique_wallets_24h: Mapped[int | None] = mapped_column(Integer)

    # Source
    blockchain: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="etherscan")
    extra_data: Mapped[dict | None] = mapped_column(JSONB)

    # Relationship
    project: Mapped[Project] = relationship(back_populates="onchain_data")

    __table_args__ = (
        Index("ix_onchain_data_project_created", "project_id", "created_at"),
    )


class WhaleActivity(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "whale_activities"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Wallet info
    wallet_address: Mapped[str] = mapped_column(String(255), nullable=False)
    wallet_label: Mapped[str | None] = mapped_column(String(255))
    is_smart_money: Mapped[bool] = mapped_column(Boolean, default=False)

    # Transaction info
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    amount_token: Mapped[float | None] = mapped_column(Float)
    amount_usd: Mapped[float | None] = mapped_column(Float)
    tx_hash: Mapped[str | None] = mapped_column(String(255))

    # Context
    blockchain: Mapped[str] = mapped_column(String(50), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    extra_data: Mapped[dict | None] = mapped_column(JSONB)

    __table_args__ = (
        Index("ix_whale_activities_project_time", "project_id", "timestamp"),
        Index("ix_whale_activities_wallet", "wallet_address"),
        Index("ix_whale_activities_action", "action"),
        Index("ix_whale_activities_smart_money", "is_smart_money"),
    )
