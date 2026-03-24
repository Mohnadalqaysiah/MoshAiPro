"""
Qaffel AI - Analysis Log Model
سجل كل تحليل يقوم به المستخدم
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class AnalysisLog(Base):
    __tablename__ = "analysis_logs"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    market      = Column(String, nullable=False, index=True)
    timeframe   = Column(String, nullable=False)

    recommendation = Column(String, nullable=True)   # BUY / SELL / WAIT / WATCH
    confidence     = Column(Float,  nullable=True)
    current_price  = Column(Float,  nullable=True)
    entry          = Column(Float,  nullable=True)
    sl             = Column(Float,  nullable=True)
    tp1            = Column(Float,  nullable=True)
    tp2            = Column(Float,  nullable=True)
    rr             = Column(Float,  nullable=True)
    lot_size       = Column(Float,  nullable=True)   # الحجم المحسوب

    from_cache  = Column(Boolean, default=False)
    full_result = Column(JSON,    nullable=True)   # كامل النتيجة من ICT engine

    created_at  = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User", back_populates="analysis_logs")

    def __repr__(self):
        return f"<AnalysisLog(id={self.id}, user={self.user_id}, {self.market}/{self.timeframe}, {self.recommendation})>"
