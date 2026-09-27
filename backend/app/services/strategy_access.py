"""
Mosh AI Pro v5 - Strategy Builder Access Tier
مشترَك بين app/api/strategies.py (الطلبات الحيّة) وapp/services/strategy_checker.py
(حلقة الرصد الخلفية) — نفس منطق الفئة بمكان واحد لا نسخة موازية قد تنحرف.

(2026-09-27) قرار صاحب المنتج: باني الاستراتيجيات صار مسيَّراً منفصلاً عن
الأسبوعي/الشهري العاديين. الوصول الكامل حصراً لـ: أدمن، السنوي (دائماً)،
باقة Premium المنفصلة (strategy_pro_until)، أو مشترك قديم (grandfathered —
استثناء تاريخي وقت إطلاق الميزة، لا يتكرر مع أي مشترك جديد).
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.user import User, UserRole, PlanType

LIMITED_MAX_STRATEGIES   = 1
LIMITED_MAX_CONDITIONS   = 1
LIMITED_BLOCKED_CATEGORY = "smc"
LIMITED_FREE_ALERTS      = 3


def access_tier(user: User, db: Session = None) -> str:
    """'full' أو 'limited'. db اختياري: مرّره لتفعيل check_subscription (تُنزّل
    اشتراكاً منتهياً لـTRIAL كأثر جانبي) — الحلقة الخلفية لا تحتاجه، الحالة
    الحيّة محدَّثة أصلاً بفعل fetch المستخدم من نفس الجلسة."""
    if user.role == UserRole.ADMIN:
        return "full"
    if db is not None:
        from app.services.auth_service import check_subscription
        check_subscription(user, db)
    if user.is_yearly_subscriber:
        return "full"
    if user.strategy_builder_grandfathered and user.plan in (PlanType.WEEKLY, PlanType.MONTHLY):
        return "full"
    if user.strategy_pro_until:
        until = user.strategy_pro_until
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        if until > datetime.now(timezone.utc):
            return "full"
    return "limited"
