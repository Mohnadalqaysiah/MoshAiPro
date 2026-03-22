"""
Mosh AI Pro v5 - User Model (Full SaaS)
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Enum as SAEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class UserRole(str, enum.Enum):
    USER  = "user"
    ADMIN = "admin"


class PlanType(str, enum.Enum):
    TRIAL   = "trial"
    WEEKLY  = "weekly"
    MONTHLY = "monthly"
    BANNED  = "banned"


class User(Base):
    __tablename__ = "users"

    id           = Column(Integer, primary_key=True, index=True)
    email        = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name    = Column(String, nullable=True)
    role         = Column(SAEnum(UserRole), default=UserRole.USER, nullable=False)

    # Telegram link (optional)
    telegram_id  = Column(String, unique=True, index=True, nullable=True)
    telegram_username = Column(String, nullable=True)

    # Plan & Subscription
    plan               = Column(SAEnum(PlanType), default=PlanType.TRIAL, nullable=False)
    is_active          = Column(Boolean, default=True)
    trial_started_at   = Column(DateTime(timezone=True), server_default=func.now())
    trial_ends_at      = Column(DateTime(timezone=True), nullable=True)
    subscription_ends_at = Column(DateTime(timezone=True), nullable=True)

    # Usage counters (reset daily)
    analyses_used_today   = Column(Integer, default=0)
    chat_used_today       = Column(Integer, default=0)
    analyses_total        = Column(Integer, default=0)
    chat_total            = Column(Integer, default=0)
    last_usage_reset      = Column(DateTime(timezone=True), server_default=func.now())

    # Trial credits (lifetime)
    trial_analyses_left   = Column(Integer, default=10)
    trial_chat_left       = Column(Integer, default=20)

    # Telegram link token (for bot linking)
    telegram_link_token   = Column(String, unique=True, nullable=True, index=True)

    # Trading Preferences (Position Sizing)
    account_balance       = Column(Float, default=10000.0)   # رأس المال الافتراضي
    risk_percent          = Column(Float, default=1.5)        # نسبة المخاطرة الافتراضية

    # Preferences
    language              = Column(String, default="ar")
    notifications_enabled = Column(Boolean, default=True)

    # Timestamps
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), onupdate=func.now())
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    payments     = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    signals      = relationship("Signal", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, plan={self.plan})>"
