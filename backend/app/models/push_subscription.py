"""
Mosh AI Pro v5 - Web Push Subscription Model
اشتراك إشعارات المتصفح (Web Push API) — قناة موازية لتيليجرام، تحديداً
لعملاء الموقع اللي ما ربطوا حسابهم بتيليجرام (لا يصلهم أي تنبيه شخصي
حالياً). مستخدم واحد قد يملك عدة اشتراكات (متصفحات/أجهزة مختلفة).
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    endpoint   = Column(String, unique=True, nullable=False)
    p256dh     = Column(String, nullable=False)
    auth       = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
