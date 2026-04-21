"""
Mosh AI Pro v5 - Price Alert Model
"""

import enum
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class AlertDirection(str, enum.Enum):
    ABOVE = "above"   # أرسل إشعار عندما يرتفع السعر فوق الهدف
    BELOW = "below"   # أرسل إشعار عندما ينخفض السعر دون الهدف


class PriceAlert(Base):
    __tablename__ = "price_alerts"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    telegram_id  = Column(String, nullable=True)   # للإرسال المباشر
    symbol       = Column(String, nullable=False)
    target_price = Column(Float, nullable=False)
    direction    = Column(SQLEnum(AlertDirection), nullable=False)
    note         = Column(String, nullable=True)   # ملاحظة اختيارية
    triggered    = Column(Boolean, default=False, index=True)
    triggered_at = Column(DateTime(timezone=True), nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="price_alerts")
