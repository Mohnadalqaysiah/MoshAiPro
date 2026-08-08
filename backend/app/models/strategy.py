"""
Mosh AI Pro v5 - Strategy Builder Models
User-defined strategies (condition groups) evaluated against the real
AI engine output, with a background checker + Telegram alerting.
"""

import enum
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, JSON,
    ForeignKey, Enum as SQLEnum
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class StrategyStatus(str, enum.Enum):
    DRAFT    = "DRAFT"
    ACTIVE   = "ACTIVE"
    DISABLED = "DISABLED"


class GroupLogic(str, enum.Enum):
    AND      = "AND"
    OR       = "OR"
    AT_LEAST = "AT_LEAST"


class Strategy(Base):
    __tablename__ = "strategies"

    id      = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    name       = Column(String, nullable=False)
    symbols    = Column(JSON, default=list)   # ["XAU/USD", ...]
    timeframes = Column(JSON, default=list)   # ["1H","15m","5m"]

    min_score = Column(Integer, default=70)

    trigger_create_signal = Column(Boolean, default=True)
    trigger_send_telegram = Column(Boolean, default=True)
    trigger_monitor_entry = Column(Boolean, default=True)

    exec_entry_type = Column(String, default="Market")
    exec_sl_type    = Column(String, default="Below Swing Low")
    exec_tp_type    = Column(String, default="Risk/Reward")
    exec_rr         = Column(Float, default=2.0)

    tg_enabled      = Column(Boolean, default=True)
    tg_chat_override = Column(String, nullable=True)   # اختياري: قناة/شات مختلف عن حساب المستخدم
    tg_send_entry      = Column(Boolean, default=True)
    tg_send_sl         = Column(Boolean, default=True)
    tg_send_tp         = Column(Boolean, default=True)
    tg_send_rr         = Column(Boolean, default=True)
    tg_send_confidence = Column(Boolean, default=True)
    tg_send_conditions = Column(Boolean, default=True)
    tg_send_chart      = Column(Boolean, default=False)

    status = Column(SQLEnum(StrategyStatus), default=StrategyStatus.DRAFT, nullable=False, index=True)

    last_triggered_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user   = relationship("User", back_populates="strategies")
    groups = relationship("StrategyGroup", back_populates="strategy",
                           cascade="all, delete-orphan", order_by="StrategyGroup.sort_order")
    events = relationship("StrategyTriggerEvent", back_populates="strategy",
                           cascade="all, delete-orphan")


class StrategyGroup(Base):
    __tablename__ = "strategy_groups"

    id          = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True)

    name       = Column(String, nullable=False)
    logic      = Column(SQLEnum(GroupLogic), default=GroupLogic.AND, nullable=False)
    at_least   = Column(Integer, default=1)
    sort_order = Column(Integer, default=0)

    strategy   = relationship("Strategy", back_populates="groups")
    conditions = relationship("StrategyCondition", back_populates="group",
                               cascade="all, delete-orphan", order_by="StrategyCondition.sort_order")


class StrategyCondition(Base):
    __tablename__ = "strategy_conditions"

    id       = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("strategy_groups.id", ondelete="CASCADE"), nullable=False, index=True)

    category = Column(String, nullable=False)   # smc / indicators / price / candles ...
    type     = Column(String, nullable=False)   # bos / rsi / fvg ...
    label    = Column(String, nullable=False)

    timeframe = Column(String, default="15m")
    tf_mode   = Column(String, default="نفس الفريم")

    value  = Column(String, nullable=True)
    weight = Column(Integer, default=10)

    enabled = Column(Boolean, default=True)
    negate  = Column(Boolean, default=False)   # NOT

    sort_order = Column(Integer, default=0)

    group = relationship("StrategyGroup", back_populates="conditions")


class StrategyTriggerEvent(Base):
    __tablename__ = "strategy_trigger_events"

    id          = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True)

    symbol    = Column(String, nullable=False)
    timeframe = Column(String, nullable=False)

    score     = Column(Integer, default=0)
    triggered = Column(Boolean, default=False, index=True)
    matched_json = Column(JSON, nullable=True)   # snapshot of per-condition results

    price          = Column(Float, nullable=True)
    telegram_sent  = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    strategy = relationship("Strategy", back_populates="events")
