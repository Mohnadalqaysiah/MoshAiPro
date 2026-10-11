"""
Mosh AI Pro v5 - Learning Games Progress
==========================================
(2026-10-11) تقدّم المستخدم في الألعاب التعليمية (/games/challenge).

قبله كانت النقاط في localStorage الزائر فقط — تضيع بتغيير الجهاز أو مسح
المتصفح ولا علاقة لها بالحساب. هنا تُحفظ لكل مستخدم مسجّل، ومنها لوحة
المتصدرين الأسبوعية.

data = نسخة كاملة من حالة اللعبة (نفس كائن P في الصفحة) — الصفحة هي مصدر
الحقيقة لتفاصيلها، والخادم يحتفظ بها ويتحقق فقط من معدّل زيادة النقاط.
"""
from sqlalchemy import Column, Integer, String, DateTime, Date, Boolean, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class GameEventDaily(Base):
    """عدّادات يومية مجهولة الهوية لقياس أثر الألعاب: visit / round_done /
    signup_click، مفصولة بين الصفحة العامة (embed=False) واللوحة (True).
    بلا أي معرّف للزائر — عدد فقط."""
    __tablename__ = "game_event_daily"

    id    = Column(Integer, primary_key=True)
    day   = Column(Date, nullable=False, index=True)
    event = Column(String, nullable=False)
    embed = Column(Boolean, nullable=False, default=False)
    count = Column(Integer, nullable=False, default=0)

    __table_args__ = (UniqueConstraint("day", "event", "embed", name="uq_game_event_daily"),)


class GameProgress(Base):
    __tablename__ = "game_progress"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    points      = Column(Integer, nullable=False, default=0)
    best_streak = Column(Integer, nullable=False, default=0)
    data        = Column(JSON, nullable=True)

    # النقاط المكتسبة هذا الأسبوع (ISO) — تُصفَّر عند تغيّر week_key
    week_key    = Column(String, nullable=True, index=True)
    week_points = Column(Integer, nullable=False, default=0)

    # تحدّي تيليجرام اليومي: آخر تحدٍّ أُجيب (YYYY-MM-DD) وسلسلة الأيام المتتالية
    daily_last   = Column(String, nullable=True)
    daily_streak = Column(Integer, nullable=True, default=0)

    updated_at  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
