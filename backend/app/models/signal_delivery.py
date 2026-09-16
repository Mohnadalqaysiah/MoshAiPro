"""
Mosh AI Pro v5 - Signal Delivery Log
=======================================
سجل من استلم كل إشارة ومتى.

(2026-09-16) لماذا وُجد: حلقة البث بـtelegram-bot/bot.py كانت ترسل لكل
مشترك ثم تزيد عدّاداً محلياً فقط وتعلّم الإشارة broadcast_sent=True —
بلا أي سجل لمن استلم. فعمود "المستخدمون" بسجل الإشارات كان يعكس عدد
صفوف Signal (أي من أُنشئت الإشارة لحسابه، غالباً حساب الماسح) لا عدد
المستلمين الفعليين — وهذا ما جعل الإشارة تبدو وكأنها وصلت لشخص واحد
بينما البث الحقيقي كان لـ~60 مشتركاً.

يسجّل المحاولات الفاشلة أيضاً (ok=False) لأنها تكشف المستخدمين الذين
حظروا البوت أو صار chat_id لديهم غير صالح — وهم فجوة صامتة كبيرة
(نصف المرتبطين تقريباً) لا تظهر بأي مكان اليوم.
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Index
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class SignalDelivery(Base):
    __tablename__ = "signal_deliveries"

    id          = Column(Integer, primary_key=True, index=True)
    signal_id   = Column(Integer, ForeignKey("signals.id"), nullable=False, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    telegram_id = Column(String, nullable=True, index=True)

    # full = النسخة الكاملة (دخول/وقف/أهداف)، masked = المموّهة بعد استهلاك الحصة
    variant     = Column(String, nullable=False, default="full")
    ok          = Column(Boolean, nullable=False, default=True, index=True)
    error       = Column(String, nullable=True)

    sent_at     = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    signal = relationship("Signal")
    user   = relationship("User")

    __table_args__ = (
        Index("ix_signal_deliveries_signal_ok", "signal_id", "ok"),
    )

    def __repr__(self):
        return (f"<SignalDelivery(signal={self.signal_id}, user={self.user_id}, "
                f"ok={self.ok}, variant={self.variant})>")
