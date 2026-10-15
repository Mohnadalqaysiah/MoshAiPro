"""
Strategy Backtest runs (2026-10-14) — نتيجة كل تشغيل باكتيست لاستراتيجية مستخدم.
يُنشأ آلياً (create_all). المنطق في app/services/strategy_backtest.py.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.sql import func
from app.database import Base


class StrategyBacktest(Base):
    __tablename__ = "strategy_backtests"

    id          = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id     = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status      = Column(String, nullable=False, default="queued")   # queued / running / done / error
    progress    = Column(Integer, nullable=False, default=0)          # 0-100
    params      = Column(JSON, nullable=True)
    result      = Column(JSON, nullable=True)
    error       = Column(Text, nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)


class StrategyTemplateCopy(Base):
    """(2026-10-15) من نسخ أي قالب جاهز — لإحصائيات الأدمن. جدول مستقل (create_all) بدل عمود بجدول strategies
    (لا ترحيل لجدول قائم). strategy_id بلا FK: النسخة قد تُحذف ويبقى أثر أنها نُسخت."""
    __tablename__ = "strategy_template_copies"

    id           = Column(Integer, primary_key=True, index=True)
    template_key = Column(String, nullable=False, index=True)
    strategy_id  = Column(Integer, nullable=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now(), index=True)
