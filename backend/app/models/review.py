"""
Reviews (2026-10-17) — آراء المشتركين (qaffel-redesign-kit المرحلة 1.5، DECISIONS.md 17/10).

مصدران فقط، وكلاهما حقيقي:
  - member:   كتبه مشترك مدفوع بعد 7 أيام على الأقل من أول دفعة مقبولة — "مشترك موثّق" (يُحسب من بياناته لا يُدّعى).
  - imported: رأي حقيقي وصل المالك خارج المنصة (رسالة تيليجرام مثلاً) أدخله الأدمن بعد موافقة صاحبه — يُوسم بمصدره ولا يحمل
              شارة "موثّق". لا تُكتب آراء مختلقة في أي مسار.
العرض: المعتمد فقط، الأحدث أولاً، والمتوسط من المعتمد فقط. لا يُرفض رأي لأنه سلبي.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.database import Base


class Review(Base):
    __tablename__ = "reviews"

    id               = Column(Integer, primary_key=True, index=True)
    user_id          = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True, unique=True)
    source           = Column(String, nullable=False, default="member")      # member | imported
    source_note      = Column(String, nullable=True)                          # imported: مثل "تيليجرام"
    rating           = Column(Integer, nullable=False)                        # 1–5
    text             = Column(Text, nullable=False)                           # 20–600
    display_name     = Column(String, nullable=False)                         # الاسم الأول + أول حرف من العائلة
    city             = Column(String, nullable=True)
    market_tag       = Column(String, nullable=True)                          # gold | crypto | forex | stocks | learn
    plan_at_review   = Column(String, nullable=True)                          # weekly | monthly | yearly
    subscribed_since = Column(DateTime(timezone=True), nullable=True)         # أول دفعة مقبولة
    status           = Column(String, nullable=False, default="pending", index=True)   # pending | approved | rejected
    admin_reply      = Column(Text, nullable=True)
    reject_reason    = Column(String, nullable=True)
    consent_public   = Column(Boolean, nullable=False, default=False)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), onupdate=func.now())
    approved_at      = Column(DateTime(timezone=True), nullable=True)
