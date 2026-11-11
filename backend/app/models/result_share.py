"""
(2026-11-11) "شارك نتيجتك" — لقطة شاشة لربح/نتيجة يرسلها المستخدم من البوت فتصل المالك مباشرة (services/result_shares.py).

لا نخزّن الصورة: file_id تيليجرام فقط (نفس قرار آراء البوت، DECISIONS 24/10) — يرسلها الخادم للمالك بنفس البوت.
consent يحفظ اختيار صاحبها: name (تُنشر باسمه) / anon (بلا اسمه) / private (للفريق فقط، لا تُنشر).
"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class ResultShare(Base):
    __tablename__ = "result_shares"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    tg_username = Column(String(64), nullable=True)
    tg_name = Column(String(128), nullable=True)
    file_kind = Column(String(16), nullable=False)        # photo | document
    file_id = Column(String, nullable=False)
    caption = Column(Text, nullable=True)
    consent = Column(String(16), nullable=False)           # name | anon | private
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    sent_to_owner_at = Column(DateTime(timezone=True), nullable=True)
