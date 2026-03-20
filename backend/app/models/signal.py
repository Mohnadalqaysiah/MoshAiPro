"""
Mosh AI Pro v5 - Signal Model
Database model for trading signals
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class SignalType(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    WATCH = "WATCH"


class SignalStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    TP1_HIT = "TP1_HIT"
    TP2_HIT = "TP2_HIT"
    SL_HIT = "SL_HIT"
    EXPIRED = "EXPIRED"


class SignalQuality(str, enum.Enum):
    STANDARD = "STANDARD"
    PREMIUM = "PREMIUM"


class Signal(Base):
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # User Reference
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Market Info
    market = Column(String, nullable=False, index=True)
    timeframe = Column(String, nullable=False)
    
    # Signal Details
    signal_type = Column(SQLEnum(SignalType), nullable=False)
    signal_quality = Column(SQLEnum(SignalQuality), default=SignalQuality.STANDARD)
    status = Column(SQLEnum(SignalStatus), default=SignalStatus.PENDING, index=True)
    
    # Price Levels
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit_1 = Column(Float, nullable=False)
    take_profit_2 = Column(Float, nullable=False)
    current_price = Column(Float, nullable=True)
    
    # AI Analysis
    ai_confidence = Column(Float, nullable=False)
    ai_reasoning = Column(JSON, nullable=True)
    
    # Strategy Components (JSON fields)
    wyckoff_phase = Column(String, nullable=True)
    liquidity_analysis = Column(JSON, nullable=True)
    volume_analysis = Column(JSON, nullable=True)
    premium_discount = Column(String, nullable=True)
    killzone = Column(String, nullable=True)
    bos_analysis = Column(JSON, nullable=True)
    
    # Risk Management
    risk_reward_ratio = Column(Float, nullable=True)
    position_size_recommended = Column(Float, nullable=True)
    
    # Performance Tracking
    profit_loss = Column(Float, default=0.0)
    profit_loss_percentage = Column(Float, default=0.0)
    entry_executed = Column(DateTime(timezone=True), nullable=True)
    exit_executed = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    signal_hash = Column(String, unique=True, index=True)
    notes = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="signals")
    analysis = relationship("Analysis", back_populates="signal", uselist=False)
    
    def __repr__(self):
        return f"<Signal(id={self.id}, market={self.market}, type={self.signal_type}, status={self.status})>"
