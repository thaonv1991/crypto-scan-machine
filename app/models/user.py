from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Enum, Column
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

import enum

class UserTier(str, enum.Enum):
    FREE = "FREE"
    PRO = "PRO"
    WHALE = "WHALE"
    ADMIN = "ADMIN"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    
    # Web3 Integration
    wallet_address: Mapped[Optional[str]] = mapped_column(String(42), unique=True, index=True, nullable=True)
    
    # Subscription Tier
    tier: Mapped[UserTier] = mapped_column(Enum(UserTier), default=UserTier.FREE)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<User {self.username} (Tier: {self.tier.value})>"
