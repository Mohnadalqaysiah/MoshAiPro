"""
Mosh AI Pro v5 - Funnel Event Model
تتبّع بسيط لمسار الاشتراك: دخل صفحة الأسعار (pricing_viewed) → بدأ الدفع
فعلاً (checkout_started). اكتمال الدفع له سجله الموثوق أصلاً بجدول Payment
(status=APPROVED) فما نكرره هون — التقرير (admin.py) يربط الاثنين وقت الطلب.

reminded_at: وقت معالجة حدث checkout_started من مهمة التذكير الخلفية
(checkout_reminder.py) — سواء أُرسل تذكير فعلي أو تبيّن إن المستخدم أكمل
الدفع أصلاً (لا داعي لتذكير)، بمجرد ما تُعالَج مرة ما تُعاد معالجتها.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class FunnelEvent(Base):
    __tablename__ = "funnel_events"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    event       = Column(String, nullable=False)   # "pricing_viewed" | "checkout_started"
    plan        = Column(String, nullable=True)     # weekly | monthly | yearly (لـcheckout_started)
    method      = Column(String, nullable=True)     # paypal | usdt | spaceremit — قد يكون فارغاً
    reminded_at = Column(DateTime(timezone=True), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now(), index=True)
