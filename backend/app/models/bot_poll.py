"""
(2026-11-14) تصويت تيليجرام من البوت — المالك: "بدنا نرسل تصويت جماعي بالبوت" (services/bot_polls.py).

BotPoll: السؤال والخيارات والجمهور وحالة الإرسال. BotPollMessage: رسالة التصويت لكل مستلم — poll_tg_id هو معرّف تيليجرام
للتصويت (يختلف لكل محادثة)، وبه نربط الإجابة بالتصويت والمستلم وفئته **لحظة الإرسال** (مدفوع/تجربة)، فتبقى النتائج صحيحة
لو تغيّرت باقة المستخدم لاحقاً. BotPollAnswer: آخر اختيار لكل مستلم (سحب التصويت يحذفه). tier="test" = تجربة الأدمن، لا تُحتسب.
"""
from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base


class BotPoll(Base):
    __tablename__ = "bot_polls"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(String(300), nullable=False)
    options = Column(JSON, nullable=False)                 # ["...", "..."] — 2..10، كل خيار ≤ 100 حرف
    allows_multiple = Column(Boolean, default=False, nullable=False)
    audience = Column(String(16), nullable=False, default="paid")   # paid | trial | all
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    done_at = Column(DateTime(timezone=True), nullable=True)
    total = Column(Integer, default=0, nullable=False)
    sent = Column(Integer, default=0, nullable=False)
    failed = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)


class BotPollMessage(Base):
    __tablename__ = "bot_poll_messages"

    id = Column(Integer, primary_key=True, index=True)
    poll_id = Column(Integer, ForeignKey("bot_polls.id"), nullable=False, index=True)
    poll_tg_id = Column(String(64), nullable=False, unique=True, index=True)
    telegram_id = Column(String, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    tier = Column(String(16), nullable=False)              # paid | trial | admin | test
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class BotPollAnswer(Base):
    __tablename__ = "bot_poll_answers"
    __table_args__ = (UniqueConstraint("poll_id", "telegram_id", name="uq_bot_poll_answer"),)

    id = Column(Integer, primary_key=True, index=True)
    poll_id = Column(Integer, ForeignKey("bot_polls.id"), nullable=False, index=True)
    telegram_id = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    tier = Column(String(16), nullable=False)
    option_ids = Column(JSON, nullable=False)
    answered_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
