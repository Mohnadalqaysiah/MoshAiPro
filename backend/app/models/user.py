"""
Mosh AI Pro v5 - User Model
Database model for user management
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Telegram Info
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    
    # Trading Preferences
    preferred_market = Column(String, default="XAUUSD")
    confidence_threshold = Column(Integer, default=60)
    enable_advanced_ai = Column(Boolean, default=True)
    
    # Subscription
    is_active = Column(Boolean, default=True)
    is_trial = Column(Boolean, default=True)
    trial_started_at = Column(DateTime(timezone=True), server_default=func.now())
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)
    subscription_ends_at = Column(DateTime(timezone=True), nullable=True)
    
    # Settings
    last_signal_hash = Column(String, nullable=True)
    notifications_enabled = Column(Boolean, default=True)
    language = Column(String, default="ar")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_active_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    signals = relationship("Signal", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, market={self.preferred_market})>"
