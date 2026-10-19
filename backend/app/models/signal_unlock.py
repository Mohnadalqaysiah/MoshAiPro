"""
Signal Unlock (2026-10-19)
==========================
سجل "أي إشارة فُتحت كاملة لأي مستخدم تجربة، وبأي يوم" — الحصة اليومية المجانية (trial_signal_daily_limit)
موحّدة بين الموقع وتيليجرام. صف واحد لكل (مستخدم، قرار، يوم): إشارة فُتحت بأي قناة تبقى مفتوحة بالقناتين
حتى نهاية اليوم ولا تُحسب مرتين.

قبله: تيليجرام بعدّاد يومي (users.signal_notif_seen_today) لا يعرف أي إشارة فتح، والموقع بـ"أحدث 3 نشطة الآن"
— فإشارة رآها مفتوحة تُقفل حين تصدر 3 أحدث منها، والقناتان تعطيان حصتين منفصلتين.
"""
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class SignalUnlock(Base):
    __tablename__ = "signal_unlocks"
    __table_args__ = (UniqueConstraint("user_id", "decision_key", "day", name="uq_signal_unlock_user_key_day"),)

    id           = Column(Integer, primary_key=True)
    user_id      = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    decision_key = Column(String(200), nullable=False)     # decision_grouping.decision_key كنص
    day          = Column(Date, nullable=False, index=True)  # يوم UTC — نفس حدّ العدّاد القديم
    channel      = Column(String(16), nullable=False)       # web / telegram
    signal_id    = Column(Integer, nullable=True)           # للتتبّع فقط
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
