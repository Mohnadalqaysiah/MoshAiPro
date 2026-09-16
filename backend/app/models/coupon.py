"""
Mosh AI Pro v5 — Discount Coupons
=================================
كوبون خصم بنسبة مئوية يُدار بالكامل من لوحة الإدارة.

قراران يحكمان التصميم:

 1) الخصم يُحسب على الخادم دائماً. الواجهة ترسل الرمز لا المبلغ، وكل
    مسار دفع (USDT / Stripe / Spaceremit) يمرّ بـcoupon_service.
    لو حُسب المبلغ على العميل لأمكن شراء اشتراك سنوي بدولار.

 2) العدّاد يزيد عند اعتماد الدفعة لا عند إنشائها. لولا ذلك لأمكن
    استنفاد كوبون محدود بإنشاء دفعات معلّقة لا تُدفع أبداً. ويقابله
    أن الحد الأقصى قد يُتجاوز مؤقتاً بدفعات معلّقة متزامنة — وهو
    احتمال مقبول هنا بحجم الاستخدام الحالي، والعكس (حجز الكوبون
    بدفعة لن تكتمل) ضرر مؤكد لا محتمل.
"""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON, Index
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Coupon(Base):
    __tablename__ = "coupons"

    id               = Column(Integer, primary_key=True, index=True)
    code             = Column(String, unique=True, index=True, nullable=False)  # يُخزَّن بحروف كبيرة
    discount_percent = Column(Float, nullable=False)                            # 1..100

    is_active        = Column(Boolean, default=True, nullable=False)
    max_uses         = Column(Integer, nullable=True)      # None = بلا حد
    used_count       = Column(Integer, default=0, nullable=False)
    per_user_limit   = Column(Integer, default=1, nullable=False)   # 0 = بلا حد
    expires_at       = Column(DateTime(timezone=True), nullable=True)

    # قائمة مفاتيح الباقات التي يسري عليها (weekly/monthly/yearly).
    # None أو [] = كل الباقات.
    plans            = Column(JSON, nullable=True)

    note             = Column(String, nullable=True)
    created_by       = Column(Integer, nullable=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), onupdate=func.now())

    redemptions      = relationship("CouponRedemption", back_populates="coupon")


class CouponRedemption(Base):
    """
    سجل استخدام فعلي — يُكتب عند اعتماد الدفعة. وجوده ضروري لا تكميلي:
    per_user_limit يُفحص عليه، وبدونه لا سبيل لمعرفة من استخدم ماذا ولا
    للتدقيق في الخصومات الممنوحة.
    """
    __tablename__ = "coupon_redemptions"

    id           = Column(Integer, primary_key=True, index=True)
    coupon_id    = Column(Integer, ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False)
    user_id      = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    payment_id   = Column(Integer, nullable=True)

    plan         = Column(String, nullable=True)
    price_before = Column(Float, nullable=True)
    price_after  = Column(Float, nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    coupon       = relationship("Coupon", back_populates="redemptions")

    __table_args__ = (
        Index("ix_coupon_redemptions_coupon_user", "coupon_id", "user_id"),
    )
