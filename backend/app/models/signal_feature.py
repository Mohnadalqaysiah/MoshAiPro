"""
Signal Features — "بصمة السوق" لحظة صدور الإشارة (2026-10-13)
================================================================
لماذا: لنتعلم من الخسائر نحتاج حالة السوق **وقت** الإشارة (قوة الاتجاه، بعد السعر عن متوسطه،
التقلب، الجلسة، حالة الكريبتو العامة...). المحرك يحسب أغلبها ثم يرميها؛ وإعادة حسابها لاحقاً
من الشموع غير ممكنة لأن الشموع القصيرة تختفي خلال أيام (تحليل تراجع 12-13/10 اصطدم بهذا).

جدول منفصل لا عمود بجدول signals: يُنشأ آلياً عند التشغيل (create_all) بلا ترحيل، ويخدم
الإشارات الحقيقية (signal_id) وإشارات الظل (shadow_id) معاً. لا يقرأه أي بث أو شاشة عميل.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.database import Base


class SignalFeature(Base):
    __tablename__ = "signal_features"

    id         = Column(Integer, primary_key=True, index=True)
    signal_id  = Column(Integer, ForeignKey("signals.id"), nullable=True, index=True)
    shadow_id  = Column(Integer, ForeignKey("shadow_signals.id"), nullable=True, index=True)
    market     = Column(String, nullable=False, index=True)
    timeframe  = Column(String, nullable=True)
    version    = Column(Integer, nullable=False, default=1)   # يرتفع إن تغيّر تعريف أي حقل
    features   = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
