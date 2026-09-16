"""
coupon_service.py — المصدر الوحيد لتسعير الكوبونات
===================================================
كل مسار دفع بالمشروع (USDT اليدوي، Stripe Checkout، Stripe PaymentIntent،
Spaceremit) يمرّ من هنا. وُحِّد عمداً: أي مسار يحسب الخصم بنفسه هو المسار
الذي سيُنسى عند تعديل القواعد، فيبيع اشتراكاً بسعر خاطئ أو يقبل كوبوناً
منتهياً — والخلل بالدفع لا يظهر بالاختبار بل بالفاتورة.

قاعدتان لا تُخترقان:
  • الواجهة ترسل الرمز، والخادم يحسب المبلغ. لا يُقبل سعر قادم من العميل.
  • العدّاد يزيد عند الاعتماد لا عند الإنشاء (راجع models/coupon.py).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from loguru import logger
from sqlalchemy.orm import Session

from app.models.coupon import Coupon, CouponRedemption


def normalize_code(code: Optional[str]) -> str:
    return (code or "").strip().upper()


def find_coupon(db: Session, code: Optional[str]) -> Optional[Coupon]:
    c = normalize_code(code)
    if not c:
        return None
    return db.query(Coupon).filter(Coupon.code == c).first()


def validate_coupon(
    db: Session,
    code: Optional[str],
    plan_key: str,
    user_id: Optional[int] = None,
) -> tuple[Optional[Coupon], Optional[str]]:
    """
    يُعيد (الكوبون، رسالة الخطأ). رمز فارغ ⇒ (None, None) — أي بلا كوبون
    وبلا خطأ، لأن الشراء بدون كوبون حالة طبيعية لا فشل.
    """
    if not normalize_code(code):
        return None, None

    coupon = find_coupon(db, code)
    if not coupon:
        return None, "رمز الخصم غير صحيح"
    if not coupon.is_active:
        return None, "رمز الخصم موقوف"

    if coupon.expires_at:
        exp = coupon.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < datetime.now(timezone.utc):
            return None, "انتهت صلاحية رمز الخصم"

    if coupon.max_uses is not None and (coupon.used_count or 0) >= coupon.max_uses:
        return None, "استُنفد عدد استخدامات رمز الخصم"

    if coupon.plans and plan_key not in coupon.plans:
        return None, "رمز الخصم لا يسري على هذه الباقة"

    if user_id and (coupon.per_user_limit or 0) > 0:
        used = (
            db.query(CouponRedemption)
              .filter(CouponRedemption.coupon_id == coupon.id,
                      CouponRedemption.user_id == user_id)
              .count()
        )
        if used >= coupon.per_user_limit:
            return None, "استخدمت هذا الرمز من قبل"

    return coupon, None


def apply_discount(price: float, coupon: Optional[Coupon]) -> float:
    """السعر بعد الخصم، مقرَّباً لسنتين ولا ينزل تحت الصفر."""
    if not coupon:
        return round(float(price), 2)
    pct = max(0.0, min(float(coupon.discount_percent or 0), 100.0))
    return round(max(float(price) * (1 - pct / 100.0), 0.0), 2)


def price_for(
    db: Session,
    plan_info: dict,
    plan_key: str,
    code: Optional[str],
    user_id: Optional[int] = None,
    strict: bool = True,
) -> tuple[float, Optional[Coupon], Optional[str]]:
    """
    التسعير النهائي لمسار دفع. يُعيد (السعر، الكوبون، الخطأ).

    strict=True  → رمز غير صالح يوقف العملية (مسارات الدفع: المستخدم أدخل
                   رمزاً ويتوقع خصمه، فتمريره بالسعر الكامل بيعٌ بسعر لم
                   يوافق عليه).
    strict=False → يُتجاهل الرمز غير الصالح ويُعاد السعر الكامل (مسارات
                   العرض فقط).
    """
    base = float(plan_info.get("price_usd") or 0)
    coupon, err = validate_coupon(db, code, plan_key, user_id)
    if err:
        if strict:
            return base, None, err
        return base, None, err
    return apply_discount(base, coupon), coupon, None


def redeem(
    db: Session,
    coupon_code: Optional[str],
    user_id: int,
    payment_id: Optional[int],
    plan_key: Optional[str],
    price_before: Optional[float],
    price_after: Optional[float],
) -> None:
    """
    يُستدعى مرة واحدة عند اعتماد الدفعة. لا يرفع استثناءً أبداً: فشل تسجيل
    الاستخدام يجب ألا يمنع تفعيل اشتراك دُفع ثمنه فعلاً — الاشتراك حق
    المستخدم، والعدّاد تفصيل محاسبي يُصلَح لاحقاً.
    """
    code = normalize_code(coupon_code)
    if not code:
        return
    try:
        coupon = db.query(Coupon).filter(Coupon.code == code).first()
        if not coupon:
            logger.warning(f"[COUPON] اعتماد دفعة برمز غير موجود: {code}")
            return
        already = (
            db.query(CouponRedemption)
              .filter(CouponRedemption.payment_id == payment_id)
              .first()
            if payment_id else None
        )
        if already:
            return   # idempotent — الويبهوك قد يُستدعى مرتين
        coupon.used_count = (coupon.used_count or 0) + 1
        db.add(CouponRedemption(
            coupon_id=coupon.id, user_id=user_id, payment_id=payment_id,
            plan=plan_key, price_before=price_before, price_after=price_after,
        ))
        logger.info(
            f"[COUPON] {code} استُخدم — user={user_id} payment={payment_id} "
            f"{price_before} → {price_after} (الإجمالي {coupon.used_count})"
        )
    except Exception as e:
        logger.error(f"[COUPON] تعذّر تسجيل استخدام {code}: {e}")
