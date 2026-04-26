"""
Trade Journal Model — يومية التداول الشخصية
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.sql import func
from app.database import Base
import enum


class TradeDirection(str, enum.Enum):
    BUY  = "BUY"
    SELL = "SELL"


class TradeResult(str, enum.Enum):
    OPEN = "OPEN"
    WIN  = "WIN"
    LOSS = "LOSS"
    BE   = "BE"   # Break-even


class TradeJournalEntry(Base):
    __tablename__ = "trade_journal"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Trade details
    symbol     = Column(String(20),  nullable=False, index=True)
    direction  = Column(SQLEnum(TradeDirection), nullable=False)
    result     = Column(SQLEnum(TradeResult),    default=TradeResult.OPEN, index=True)

    # Price levels
    entry_price  = Column(Float, nullable=True)
    exit_price   = Column(Float, nullable=True)
    stop_loss    = Column(Float, nullable=True)
    take_profit  = Column(Float, nullable=True)
    lot_size     = Column(Float, nullable=True)

    # P&L
    pnl_pips  = Column(Float, nullable=True)   # نقاط الربح/الخسارة
    pnl_usd   = Column(Float, nullable=True)   # بالدولار

    # Metadata
    notes      = Column(Text,    nullable=True)
    strategy   = Column(String(100), nullable=True)   # OB, FVG, Sweep…
    timeframe  = Column(String(10),  nullable=True)
    screenshot = Column(String(500), nullable=True)   # URL للصورة

    # Timestamps
    opened_at  = Column(DateTime(timezone=True), nullable=True)
    closed_at  = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
