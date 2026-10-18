"""
Shadow Signals (2026-10-12)
============================
إشارات تُحسب ولا تُرسل: كريبتو عطلة نهاية الأسبوع (راجع app/services/weekend_policy.py).
جدول منفصل عن signals عمداً — لا يقرأه أي بث أو شاشة أو إحصائية للعملاء.

أسماء الحقول مطابقة لـSignal (entry_price/stop_loss/take_profit_1/...، created_at،
expires_at، status) حتى تقيّمها نفس أداة التحقق من الشموع (_verify_signal_outcome_core).
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class ShadowSignal(Base):
    __tablename__ = "shadow_signals"

    id                = Column(Integer, primary_key=True, index=True)
    source            = Column(String, nullable=False)        # scanner / analyze / web / watch
    reason            = Column(String, nullable=False, default="crypto_weekend")
    market            = Column(String, nullable=False, index=True)
    timeframe         = Column(String, nullable=True)
    signal_type       = Column(String, nullable=False)        # BUY / SELL
    entry_price       = Column(Float, nullable=False)
    stop_loss         = Column(Float, nullable=False)
    take_profit_1     = Column(Float, nullable=False)
    take_profit_2     = Column(Float, nullable=True)
    ai_confidence     = Column(Float, nullable=True)
    risk_reward_ratio = Column(Float, nullable=True)
    user_id           = Column(Integer, ForeignKey("users.id"), nullable=True)
    signal_hash       = Column(String, unique=True, index=True)
    status            = Column(String, nullable=False, default="SHADOW")
    created_at        = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    expires_at        = Column(DateTime(timezone=True), nullable=True)

    # تُملأ آلياً بعد انتهاء المدة (app/services/shadow_evaluator.py) — شموع 5m المتاحة
    # تغطي ~3.5 أيام فقط، فالتقييم لا يُترك لوقت المراجعة.
    outcome           = Column(String, nullable=True)   # TP1_HIT/TP2_HIT/SL_HIT/EXPIRED_*/NOT_TRIGGERED/NO_DATA
    r_multiple        = Column(Float, nullable=True)
    entry_time        = Column(DateTime(timezone=True), nullable=True)
    exit_time         = Column(DateTime(timezone=True), nullable=True)
    evaluated_at      = Column(DateTime(timezone=True), nullable=True)
    # (2026-10-18) نسخة التحقق من المستويات (app/services/shadow_levels.py). NULL = قبل الإصلاح: قد تكون المستويات
    # معكوسة (تدقيق 18/10: 299 من 793). 1 = مرّت بنفس فحص الجهة الحي. السجلات القديمة لا تُعدَّل ولا تُحذف.
    levels_version    = Column(Integer, nullable=True, index=True)
