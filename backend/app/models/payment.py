"""
Mosh AI Pro v5 - Payment Model
USDT payments via Binance wallet
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Enum as SAEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class PaymentStatus(str, enum.Enum):
    PENDING  = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PaymentPlan(str, enum.Enum):
    WEEKLY  = "weekly"
    MONTHLY = "monthly"
    # (2026-09-16) السنوية باقة دفع لا باقة مستخدم. المقابل على users.plan
    # يبقى MONTHLY بمدة 365 يوماً عمداً: PlanType.WEEKLY/MONTHLY مكتوبان
    # يدوياً كـ"الباقات المدفوعة" في ~25 موضعاً بثمانية ملفات (bot.py
    # فلتر المشتركين، signals.py، chat.py حدود الرسائل، auth.py،
    # affiliate.py، إحصاءات admin.py). فإضافة PlanType.YEARLY كانت
    # ستُسقط المشترك السنوي صامتاً من كل تلك الفحوص — أي يدفع ولا تصله
    # إشارة. الثمن أن شارة الباقة تقول "monthly" لمن اشترك سنوياً،
    # وتاريخ الانتهاء يظهر صحيحاً. تُصلَح الشارة بتوحيد الفحوص في ثابت
    # PAID_PLANS واحد، وهو تعديل مستقل لا يُخلط بإطلاق السنوية.
    YEARLY  = "yearly"


class Payment(Base):
    __tablename__ = "payments"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    plan        = Column(SAEnum(PaymentPlan), nullable=False)
    amount_usd  = Column(Float, nullable=False)          # 7 or 30
    network     = Column(String, default="TRC20")        # TRC20 / BEP20 / stripe
    tx_id       = Column(String, unique=True, nullable=False)  # Binance TxID or Stripe Checkout Session ID

    provider    = Column(String, default="usdt", nullable=False)  # "usdt" | "stripe"
    stripe_payment_intent = Column(String, nullable=True)

    # (2026-09-16) الكوبون يُسجَّل على الدفعة نفسها لا على المستخدم:
    # السعر المخفَّض يُثبَّت لحظة الإنشاء، فلا يتغيّر إن عُدِّل الكوبون أو
    # أُلغي قبل الاعتماد. وبدونه لا سبيل لتدقيق سبب اختلاف amount_usd عن
    # سعر الباقة المعلن.
    coupon_code      = Column(String, nullable=True)
    discount_percent = Column(Float, nullable=True)

    status      = Column(SAEnum(PaymentStatus), default=PaymentStatus.PENDING)
    admin_note  = Column(String, nullable=True)
    approved_by = Column(Integer, nullable=True)          # admin user id

    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())

    user        = relationship("User", back_populates="payments")
