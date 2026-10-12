"""
Telegram Broadcast Log (2026-10-11)
====================================
سجل لكل إعلان يُرسل من لوحة الإدارة (رسائل تيليجرام): متى، من أرسله، نصّه
المختصر، وكم مستلماً نجح وكم فشل.

قبله لم يكن هناك أي سجل: البث الكبير (> 5) يجري بالخلفية ويعيد للوحة
"جاري إرسال N" دائماً، حتى لو فشلت كل الرسائل — فلا طريقة لمعرفة هل وصل
الإعلان أصلاً.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.database import Base


class TelegramBroadcast(Base):
    __tablename__ = "telegram_broadcasts"

    id          = Column(Integer, primary_key=True, index=True)
    admin_id    = Column(Integer, ForeignKey("users.id"), nullable=True)
    title       = Column(String, nullable=True)
    preview     = Column(Text, nullable=True)
    total       = Column(Integer, nullable=False, default=0)
    ok          = Column(Integer, nullable=False, default=0)
    failed      = Column(Integer, nullable=False, default=0)
    last_error  = Column(String, nullable=True)
    status      = Column(String, nullable=False, default="sending")   # sending / done
    created_at  = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
