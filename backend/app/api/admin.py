"""
Mosh AI Pro v5 - Admin API
Full control: Users, Payments, Markets
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from loguru import logger
import requests
from app.services.email_service import send_email as _send_email_svc

from app.database import get_db
from app.models.user import User, UserRole, PlanType
from app.models.payment import Payment, PaymentStatus, PaymentPlan
from app.models.market_config import MarketConfig
from app.models.site_settings import SiteSettings
from app.models.affiliate import Affiliate, AffiliateReferral, TIER1_RATE, TIER2_RATE, TIER2_THRESHOLD
from app.models.signal import Signal, SignalStatus
from app.services.auth_service import get_admin_user, hash_password, verify_password
from app.services.smart_data import smart_data as _smart_data
from app.config import get_settings

_settings = get_settings()

router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────────────────────────

class UserUpdateIn(BaseModel):
    plan:       Optional[str] = None
    is_active:  Optional[bool] = None
    extra_days: Optional[int] = None   # تمديد الاشتراك
    admin_note: Optional[str] = None   # ملاحظة الإدارة

class PaymentActionIn(BaseModel):
    action:     str   # approve | reject
    admin_note: str = ""

class SettingIn(BaseModel):
    value: str

class AdminProfileIn(BaseModel):
    new_email:    Optional[str] = None
    new_password: Optional[str] = None
    current_password: str

class MarketIn(BaseModel):
    symbol:       str
    display_name: str
    category:     str = "forex"
    is_active:    bool = True
    is_premium:   bool = False
    yf_symbol:    str = ""
    td_symbol:    str = ""
    sort_order:   int = 0

class TelegramMessageIn(BaseModel):
    title: Optional[str] = None  # العنوان الرئيسي مثل "Qaffel Ai"
    message: str  # الرسالة
    user_ids: Optional[List[int]] = None  # إذا None، يرسل لجميع المستخدمين الذين لديهم telegram_id


# ─── Dashboard Stats ──────────────────────────────────────────────────────────

@router.get("/stats")
def admin_stats(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    total_users   = db.query(User).count()
    trial_users   = db.query(User).filter(User.plan == PlanType.TRIAL).count()
    weekly_users  = db.query(User).filter(User.plan == PlanType.WEEKLY).count()
    monthly_users = db.query(User).filter(User.plan == PlanType.MONTHLY).count()
    banned_users  = db.query(User).filter(User.plan == PlanType.BANNED).count()
    active_markets = db.query(MarketConfig).filter(MarketConfig.is_active == True).count()

    pending_payments = db.query(Payment).filter(
        Payment.status == PaymentStatus.PENDING
    ).count()
    approved_payments = db.query(Payment).filter(
        Payment.status == PaymentStatus.APPROVED
    ).all()
    total_revenue = sum(p.amount_usd for p in approved_payments)

    return {
        "users": {
            "total":   total_users,
            "trial":   trial_users,
            "weekly":  weekly_users,
            "monthly": monthly_users,
            "banned":  banned_users,
        },
        "payments": {
            "pending": pending_payments,
            "revenue_usd": total_revenue,
        },
        "markets": {
            "active": active_markets,
        }
    }


# ─── Users ────────────────────────────────────────────────────────────────────

@router.get("/users")
def list_users(
    skip: int = 0,
    limit: int = 50,
    search: str = Query(default=""),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    q = db.query(User)
    if search:
        q = q.filter(
            User.email.ilike(f"%{search}%") |
            User.full_name.ilike(f"%{search}%") |
            User.telegram_id.ilike(f"%{search}%")
        )
    users = q.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    total = q.count()
    return {"total": total, "users": [_user_info(u) for u in users]}


@router.get("/users/{user_id}")
def get_user(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "المستخدم غير موجود")
    payments = db.query(Payment).filter(Payment.user_id == user_id).all()
    info = _user_info(user)
    info["payments"] = [_payment_info(p) for p in payments]
    return info


@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    data: UserUpdateIn,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "المستخدم غير موجود")

    now = datetime.now(timezone.utc)

    if data.plan is not None:
        try:
            user.plan = PlanType(data.plan)
        except ValueError:
            raise HTTPException(400, f"خطة غير صحيحة: {data.plan}")

        # ضبط تواريخ الاشتراك
        if data.plan == "weekly":
            user.subscription_ends_at = now + timedelta(days=7)
        elif data.plan == "monthly":
            user.subscription_ends_at = now + timedelta(days=30)

    if data.is_active is not None:
        user.is_active = data.is_active

    if data.extra_days:
        base = user.subscription_ends_at or now
        user.subscription_ends_at = base + timedelta(days=data.extra_days)

    db.commit()
    logger.info(f"👤 Admin updated user {user_id}: plan={data.plan}, active={data.is_active}")
    return {"success": True, "user": _user_info(user)}


@router.post("/users/{user_id}/reset-trial")
def reset_trial(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """إعادة تعيين كريدت التجربة المجانية"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "المستخدم غير موجود")
    now = datetime.now(timezone.utc)
    # اقرأ الحدود من SiteSettings (إذا عدّلها الأدمن) أو استخدم الافتراضي
    def _get_int(key: str, default: int) -> int:
        r = db.query(SiteSettings).filter(SiteSettings.key == key).first()
        try: return int(r.value) if r and r.value else default
        except: return default

    user.plan                = PlanType.TRIAL
    user.trial_analyses_left = _get_int("trial_analysis_limit", 10)
    user.trial_chat_left     = _get_int("trial_chat_limit", 20)
    user.trial_started_at    = now
    user.trial_ends_at       = now + timedelta(days=7)
    user.subscription_ends_at = None
    user.is_active           = True
    db.commit()
    logger.info(f"🔄 Trial reset for user {user_id}")
    return {"success": True, "message": "تم إعادة تعيين التجربة"}


class RenewUserIn(BaseModel):
    days:             int    = 30
    plan:             str    = "monthly"   # monthly | weekly
    reason:           str    = ""
    notify_telegram:  bool   = True


class BulkRenewIn(BaseModel):
    user_ids:        Optional[List[int]] = None   # None = all expired
    days:            int  = 30
    plan:            str  = "monthly"
    reason:          str  = ""
    notify_telegram: bool = True


@router.post("/users/{user_id}/renew")
def renew_user(
    user_id: int,
    data: RenewUserIn,
    background: BackgroundTasks,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """تجديد اشتراك مستخدم واحد مع إشعار تلغرام اختياري"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "المستخدم غير موجود")

    now   = datetime.now(timezone.utc)
    base  = max(user.subscription_ends_at or now, now)
    new_end = base + timedelta(days=data.days)

    try:
        plan_enum = PlanType(data.plan)
    except ValueError:
        plan_enum = PlanType.MONTHLY

    user.plan                = plan_enum
    user.is_active           = True
    user.subscription_ends_at = new_end
    db.commit()

    logger.info(
        f"🔄 Renewal: user={user.email} days={data.days} "
        f"plan={data.plan} reason={data.reason!r} new_end={new_end.date()}"
    )

    if data.notify_telegram and user.telegram_id:
        plan_label = {"monthly": "شهري", "weekly": "أسبوعي"}.get(data.plan, data.plan)
        msg = (
            f"✅ <b>تم تجديد اشتراكك</b>\n\n"
            f"الباقة: <b>{plan_label}</b>\n"
            f"المدة المضافة: <b>{data.days} يوم</b>\n"
            f"ينتهي في: <b>{new_end.strftime('%Y-%m-%d')}</b>"
        )
        if data.reason:
            msg += f"\nالسبب: {data.reason}"
        background.add_task(_send_telegram_message, user.telegram_id, msg)

    return {
        "success":       True,
        "user_id":       user.id,
        "email":         user.email,
        "plan":          user.plan.value,
        "new_end":       new_end.isoformat(),
        "days_added":    data.days,
        "notified":      bool(data.notify_telegram and user.telegram_id),
    }


@router.post("/users/bulk-renew")
def bulk_renew(
    data: BulkRenewIn,
    background: BackgroundTasks,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """تجديد جماعي — إما قائمة محددة أو جميع المنتهيين"""
    now = datetime.now(timezone.utc)

    if data.user_ids:
        users = db.query(User).filter(User.id.in_(data.user_ids)).all()
    else:
        # جميع المنتهيين (subscription_ends_at < now أو فارغة + plan ليس trial/banned)
        users = db.query(User).filter(
            User.plan.in_([PlanType.WEEKLY, PlanType.MONTHLY]),
            (User.subscription_ends_at < now) | (User.subscription_ends_at == None),  # noqa
        ).all()

    if not users:
        return {"success": True, "renewed": 0, "message": "لا يوجد مستخدمون منتهون"}

    try:
        plan_enum = PlanType(data.plan)
    except ValueError:
        plan_enum = PlanType.MONTHLY

    plan_label = {"monthly": "شهري", "weekly": "أسبوعي"}.get(data.plan, data.plan)
    renewed, notified = 0, 0

    for user in users:
        base    = max(user.subscription_ends_at or now, now)
        new_end = base + timedelta(days=data.days)
        user.plan                = plan_enum
        user.is_active           = True
        user.subscription_ends_at = new_end
        renewed += 1

        if data.notify_telegram and user.telegram_id:
            msg = (
                f"✅ <b>تم تجديد اشتراكك</b>\n\n"
                f"الباقة: <b>{plan_label}</b>\n"
                f"المدة المضافة: <b>{data.days} يوم</b>\n"
                f"ينتهي في: <b>{new_end.strftime('%Y-%m-%d')}</b>"
            )
            if data.reason:
                msg += f"\nالسبب: {data.reason}"
            background.add_task(_send_telegram_message, user.telegram_id, msg)
            notified += 1

    db.commit()
    logger.info(
        f"🔄 Bulk renewal: renewed={renewed} notified={notified} "
        f"days={data.days} plan={data.plan} reason={data.reason!r}"
    )
    return {
        "success":  True,
        "renewed":  renewed,
        "notified": notified,
        "days_added": data.days,
        "plan":     data.plan,
    }


@router.delete("/users/{user_id}/ban")
def ban_user(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "المستخدم غير موجود")
    user.plan = PlanType.BANNED
    user.is_active = False
    db.commit()
    return {"success": True, "message": f"تم حظر {user.email}"}


@router.delete("/users/{user_id}")
def delete_user_permanent(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """حذف نهائي للمستخدم من قاعدة البيانات"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "المستخدم غير موجود")
    if user.role == "admin":
        raise HTTPException(400, "لا يمكن حذف حساب الإدارة")
    email = user.email
    db.delete(user)
    db.commit()
    logger.info(f"🗑️ User permanently deleted: {email}")
    return {"success": True, "message": f"تم حذف {email} نهائياً"}


# ─── Payments ────────────────────────────────────────────────────────────────

@router.get("/payments")
def list_payments(
    status_filter: str = "pending",
    skip: int = 0,
    limit: int = 50,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    q = db.query(Payment)
    if status_filter != "all":
        try:
            q = q.filter(Payment.status == PaymentStatus(status_filter))
        except ValueError:
            pass
    payments = q.order_by(Payment.created_at.desc()).offset(skip).limit(limit).all()
    total = q.count()
    return {"total": total, "payments": [_payment_full(p, db) for p in payments]}


@router.put("/payments/{payment_id}")
def handle_payment(
    payment_id: int,
    data: PaymentActionIn,
    background: BackgroundTasks,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(404, "الدفع غير موجود")

    now = datetime.now(timezone.utc)

    if data.action == "approve":
        payment.status     = PaymentStatus.APPROVED
        payment.admin_note = data.admin_note
        payment.approved_by = admin.id

        # فعّل اشتراك المستخدم
        user = db.query(User).filter(User.id == payment.user_id).first()
        if user:
            days = 7 if payment.plan == PaymentPlan.WEEKLY else 30
            # إذا عنده اشتراك نشط → أضف أيام
            if user.subscription_ends_at and user.subscription_ends_at > now:
                user.subscription_ends_at += timedelta(days=days)
            else:
                user.subscription_ends_at = now + timedelta(days=days)

            user.plan      = PlanType(payment.plan.value)
            user.is_active = True
            logger.info(f"✅ Payment approved: user={user.email} plan={payment.plan} days={days}")

            # ── Affiliate commission ──────────────────────────────────────
            if user.referred_by_code:
                ref_aff = db.query(Affiliate).filter(
                    Affiliate.code == user.referred_by_code
                ).first()
                if ref_aff:
                    already = db.query(AffiliateReferral).filter(
                        AffiliateReferral.payment_id == payment.id
                    ).first()
                    if not already:
                        rate = TIER2_RATE if ref_aff.total_referrals >= TIER2_THRESHOLD else TIER1_RATE
                        tier = 2 if ref_aff.total_referrals >= TIER2_THRESHOLD else 1
                        commission = round(payment.amount_usd * rate, 4)
                        db.add(AffiliateReferral(
                            affiliate_id       = ref_aff.id,
                            referred_user_id   = user.id,
                            payment_id         = payment.id,
                            payment_amount_usd = payment.amount_usd,
                            commission_rate    = rate,
                            commission_usd     = commission,
                            tier               = tier,
                        ))
                        ref_aff.total_referrals     += 1
                        ref_aff.pending_balance_usd += commission
                        # ── +50 نقطة إحالة للمُحيل عند اشتراك المدعو ──────
                        if ref_user := db.query(User).filter(User.id == ref_aff.user_id).first():
                            ref_user.referral_points = (ref_user.referral_points or 0) + 50
                        logger.info(
                            f"💰 Affiliate commission: referrer_id={ref_aff.user_id} "
                            f"tier={tier} rate={rate*100:.0f}% earned={commission}$ +50pts"
                        )
                        # إيميل إشعار عمولة للمُحيل
                        ref_user = db.query(User).filter(User.id == ref_aff.user_id).first()
                        if ref_user and _settings.SMTP_PASSWORD:
                            from app.services.email_service import send_email, affiliate_commission_email_body
                            body = affiliate_commission_email_body(
                                name=ref_user.full_name or ref_user.email,
                                commission_usd=commission,
                                referral_name=user.full_name or user.email,
                                tier=tier,
                                pending_balance=ref_aff.pending_balance_usd + commission,
                            )
                            background.add_task(
                                send_email, ref_user.email,
                                f"💰 عمولة جديدة ${commission:.2f} — Qaffel AI",
                                body, _settings.SMTP_PASSWORD,
                            )

    elif data.action == "reject":
        payment.status     = PaymentStatus.REJECTED
        payment.admin_note = data.admin_note
        logger.info(f"❌ Payment rejected: id={payment_id}")
    else:
        raise HTTPException(400, "action يجب أن يكون approve أو reject")

    db.commit()

    # ── إيميل إشعار للمستخدم بعد الـ commit ──────────────────────────────
    if _settings.SMTP_PASSWORD:
        from app.services.email_service import (
            send_email, payment_approved_email_body, payment_rejected_email_body
        )
        _user = db.query(User).filter(User.id == payment.user_id).first()
        if _user:
            if data.action == "approve":
                days = 7 if payment.plan == PaymentPlan.WEEKLY else 30
                ends_str = (_user.subscription_ends_at.strftime("%Y-%m-%d")
                            if _user.subscription_ends_at else "—")
                body = payment_approved_email_body(
                    _user.full_name or _user.email,
                    payment.plan.value, days, ends_str,
                )
                background.add_task(
                    send_email, _user.email,
                    "✅ تم تفعيل اشتراكك — Qaffel AI", body, _settings.SMTP_PASSWORD,
                )
            elif data.action == "reject":
                body = payment_rejected_email_body(
                    _user.full_name or _user.email,
                    payment.plan.value, data.admin_note or "",
                )
                background.add_task(
                    send_email, _user.email,
                    "❌ تعذّر قبول دفعتك — Qaffel AI", body, _settings.SMTP_PASSWORD,
                )

    return {"success": True, "payment": _payment_info(payment)}


# ─── Markets ──────────────────────────────────────────────────────────────────

@router.get("/markets")
def list_markets(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    markets = db.query(MarketConfig).order_by(MarketConfig.sort_order).all()
    return [_market_info(m) for m in markets]


@router.post("/markets")
def add_market(
    data: MarketIn,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    if db.query(MarketConfig).filter(MarketConfig.symbol == data.symbol.upper()).first():
        raise HTTPException(400, "الزوج موجود مسبقاً")

    m = MarketConfig(
        symbol       = data.symbol.upper(),
        display_name = data.display_name,
        category     = data.category,
        is_active    = data.is_active,
        is_premium   = data.is_premium,
        yf_symbol    = data.yf_symbol,
        td_symbol    = data.td_symbol,
        sort_order   = data.sort_order,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    logger.info(f"➕ Market added: {m.symbol}")
    return _market_info(m)


@router.put("/markets/{symbol}")
def update_market(
    symbol: str,
    data: MarketIn,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    m = db.query(MarketConfig).filter(MarketConfig.symbol == symbol.upper()).first()
    if not m:
        raise HTTPException(404, "الزوج غير موجود")
    m.display_name = data.display_name
    m.category     = data.category
    m.is_active    = data.is_active
    m.is_premium   = data.is_premium
    m.yf_symbol    = data.yf_symbol
    m.td_symbol    = data.td_symbol
    m.sort_order   = data.sort_order
    db.commit()
    return _market_info(m)


@router.delete("/markets/{symbol}")
def delete_market(
    symbol: str,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    m = db.query(MarketConfig).filter(MarketConfig.symbol == symbol.upper()).first()
    if not m:
        raise HTTPException(404, "الزوج غير موجود")
    db.delete(m)
    db.commit()
    return {"success": True}


@router.patch("/markets/{symbol}/toggle")
def toggle_market(
    symbol: str,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    m = db.query(MarketConfig).filter(MarketConfig.symbol == symbol.upper()).first()
    if not m:
        raise HTTPException(404, "الزوج غير موجود")
    m.is_active = not m.is_active
    db.commit()
    return {"symbol": m.symbol, "is_active": m.is_active}


# ─── Expiring Soon (for Bot) ──────────────────────────────────────────────────

@router.get("/expiring-soon")
def get_expiring_users(
    days: int = 2,
    db: Session = Depends(get_db)
):
    """
    يرجع المستخدمين الذين اشتراكهم ينتهي خلال X أيام
    (بدون auth لأن البوت يستخدمه مباشرة)
    """
    now = datetime.now(timezone.utc)
    deadline = now + timedelta(days=days)

    # اشتراك مدفوع ينتهي قريباً
    paid_expiring = db.query(User).filter(
        User.plan.in_([PlanType.WEEKLY, PlanType.MONTHLY]),
        User.subscription_ends_at != None,
        User.subscription_ends_at <= deadline,
        User.telegram_id != None,
        User.is_active == True,
    ).all()

    # تجربة منتهية
    trial_expired = db.query(User).filter(
        User.plan == PlanType.TRIAL,
        User.trial_ends_at != None,
        User.trial_ends_at <= now,
        User.telegram_id != None,
        User.is_active == True,
    ).all()

    result = []
    for u in paid_expiring + trial_expired:
        days_left = 0
        if u.plan in [PlanType.WEEKLY, PlanType.MONTHLY] and u.subscription_ends_at:
            delta = u.subscription_ends_at - now
            days_left = max(0, delta.days)
        elif u.trial_ends_at:
            delta = u.trial_ends_at - now
            days_left = max(0, delta.days)

        result.append({
            "telegram_id": u.telegram_id,
            "full_name":   u.full_name or u.email,
            "plan":        u.plan,
            "days_left":   days_left,
        })

    return {"users": result, "count": len(result)}


@router.post("/email/subscription-warnings")
def send_subscription_warnings(
    days_before: int = Query(default=3, ge=1, le=7),
    background: BackgroundTasks = None,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """
    يرسل إيميل تحذير لكل من اشتراكه ينتهي خلال X أيام وليس لديه تيليجرام
    """
    from app.services.email_service import send_email, subscription_expiry_email_body
    smtp_pass = _settings.SMTP_PASSWORD
    if not smtp_pass:
        raise HTTPException(503, "SMTP غير مُعدّ")

    now      = datetime.now(timezone.utc)
    deadline = now + timedelta(days=days_before)

    # اشتراك مدفوع ينتهي قريباً + بدون تيليجرام
    users = db.query(User).filter(
        User.plan.in_([PlanType.WEEKLY, PlanType.MONTHLY]),
        User.subscription_ends_at != None,
        User.subscription_ends_at > now,
        User.subscription_ends_at <= deadline,
        User.telegram_id == None,
        User.is_active == True,
    ).all()

    sent = 0
    for u in users:
        days_left = max(0, (u.subscription_ends_at - now).days)
        body = subscription_expiry_email_body(u.full_name or u.email, days_left)
        subject = f"⚠️ اشتراكك ينتهي خلال {days_left} {'يوم' if days_left > 1 else 'أيام'} — Qaffel AI"
        if background:
            background.add_task(send_email, u.email, subject, body, smtp_pass)
        else:
            send_email(u.email, subject, body, smtp_pass)
        sent += 1

    logger.info(f"📧 Subscription warnings sent: {sent} users (≤{days_before}d, no Telegram)")
    return {"sent": sent, "days_before": days_before}


# ─── Admin Profile ────────────────────────────────────────────────────────────

@router.put("/profile")
def update_admin_profile(
    data: AdminProfileIn,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """يسمح للأدمن بتغيير إيميله أو كلمة مروره"""
    if not verify_password(data.current_password, admin.password_hash):
        raise HTTPException(400, "كلمة المرور الحالية غير صحيحة")

    if data.new_email:
        email = data.new_email.lower().strip()
        existing = db.query(User).filter(User.email == email, User.id != admin.id).first()
        if existing:
            raise HTTPException(400, "البريد الإلكتروني مستخدم من حساب آخر")
        admin.email = email

    if data.new_password:
        if len(data.new_password) < 8:
            raise HTTPException(400, "كلمة المرور يجب أن تكون 8 أحرف على الأقل")
        admin.password_hash = hash_password(data.new_password)

    db.commit()
    logger.info(f"🔐 Admin profile updated: {admin.email}")
    return {"success": True, "email": admin.email}


# ─── Site Settings ────────────────────────────────────────────────────────────

@router.get("/settings")
def get_settings_admin(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    rows = db.query(SiteSettings).all()
    return {r.key: {"value": r.value, "description": r.description} for r in rows}


@router.put("/settings/{key}")
def update_setting(
    key: str,
    data: SettingIn,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    row = db.query(SiteSettings).filter(SiteSettings.key == key).first()
    if not row:
        # Auto-create for new keys (e.g. pricing plan overrides)
        row = SiteSettings(key=key, value=data.value.strip(), description=f"Auto-created: {key}")
        db.add(row)
        db.commit()
        db.refresh(row)
        logger.info(f"⚙️ Setting created: {key} = {data.value}")
        return {"success": True, "key": key, "value": row.value}
    row.value = data.value.strip()
    db.commit()
    logger.info(f"⚙️ Setting updated: {key} = {data.value}")

    # عند تغيير TwelveData — حدّث الـ runtime مباشرة بدون إعادة تشغيل
    if key in ("twelvedata_api_key", "twelvedata_enabled"):
        td_key_row = db.query(SiteSettings).filter(SiteSettings.key == "twelvedata_api_key").first()
        td_en_row  = db.query(SiteSettings).filter(SiteSettings.key == "twelvedata_enabled").first()
        api_key  = (td_key_row.value or "").strip() if td_key_row else ""
        enabled  = (td_en_row.value or "false").strip().lower() == "true" if td_en_row else False
        _smart_data.update_twelvedata_config(api_key, enabled)

    return {"success": True, "key": key, "value": row.value}


# ─── Email ────────────────────────────────────────────────────────────────────

class EmailSendIn(BaseModel):
    subject: str
    body: str
    user_id: Optional[int] = None   # None = أرسل للكل

def _send_one(to_email: str, subject: str, body: str):
    return _send_email_svc(to_email, subject, body, _settings.SMTP_PASSWORD)

def _send_bulk(emails: List[str], subject: str, body: str):
    ok = fail = 0
    for em in emails:
        if _send_one(em, subject, body):
            ok += 1
        else:
            fail += 1
    logger.info(f"📧 Bulk email done: {ok} sent, {fail} failed")

@router.post("/email/send")
def send_email(
    data: EmailSendIn,
    background: BackgroundTasks,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """إرسال إيميل للكل أو لمستخدم معين"""
    if not _settings.SMTP_USER or not _settings.SMTP_PASSWORD:
        raise HTTPException(400, "SMTP غير مضبوط — أضف SMTP_USER و SMTP_PASSWORD في إعدادات البيئة")

    if data.user_id:
        u = db.query(User).filter(User.id == data.user_id).first()
        if not u:
            raise HTTPException(404, "المستخدم غير موجود")
        background.add_task(_send_one, u.email, data.subject, data.body)
        return {"message": f"تم إرسال الإيميل لـ {u.email}", "count": 1}
    else:
        emails = [u.email for u in db.query(User.email).filter(User.is_active == True).all()]
        background.add_task(_send_bulk, emails, data.subject, data.body)
        return {"message": f"جاري إرسال {len(emails)} إيميل في الخلفية", "count": len(emails)}


# ─── Telegram Messages ────────────────────────────────────────────────────────

def _send_telegram_message(chat_id: str, text: str) -> bool:
    """إرسال رسالة تيليجرام واحدة"""
    url = f"https://api.telegram.org/bot{_settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 429:
            import time as _t
            retry_after = resp.json().get("parameters", {}).get("retry_after", 5)
            _t.sleep(retry_after)
            resp = requests.post(url, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception:
        return False


def _broadcast_task(chat_ids: list, text: str):
    """يُرسل للقائمة في الخلفية مع rate limiting"""
    import time as _t
    for cid in chat_ids:
        _send_telegram_message(cid, text)
        _t.sleep(0.05)  # Telegram: max 30 msg/s


@router.post("/telegram/send")
def send_telegram_message(
    data: TelegramMessageIn,
    background: BackgroundTasks,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """إرسال رسالة تيليجرام — للمحددين أو للجميع"""
    if not _settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(400, "TELEGRAM_BOT_TOKEN غير مضبوط")

    # ── بناء الرسالة ───────────────────────────────────────────────────────
    lines = []
    if data.title:
        lines.append(f"<b>📢 {data.title}</b>")
        lines.append("")
    lines.append(data.message)
    lines.append("")
    lines.append("<i>— Qaffel AI</i>")
    text = "\n".join(lines)

    # ── تحديد المستلمين ────────────────────────────────────────────────────
    if data.user_ids:
        users = db.query(User).filter(
            User.id.in_(data.user_ids),
            User.telegram_id != None,
        ).all()
    else:
        users = db.query(User).filter(
            User.telegram_id != None,
            User.is_active == True,
            User.plan != PlanType.BANNED,
        ).all()

    chat_ids = [u.telegram_id for u in users if u.telegram_id]
    total    = len(chat_ids)

    if total == 0:
        return {"message": "لا يوجد مستخدمون لديهم تيليجرام", "sent": 0, "total": 0}

    # ── إرسال فوري للأعداد الصغيرة، خلفية للكبيرة ─────────────────────────
    if total <= 5:
        sent = sum(1 for cid in chat_ids if _send_telegram_message(cid, text))
        return {"message": f"✅ تم إرسال {sent}/{total} رسالة", "sent": sent, "total": total}
    else:
        background.add_task(_broadcast_task, chat_ids, text)
        return {"message": f"⏳ جاري إرسال {total} رسالة في الخلفية", "sent": total, "total": total}


# ─── Signal Performance ───────────────────────────────────────────────────────

class SignalOutcomeIn(BaseModel):
    status: str  # "TP1_HIT", "TP2_HIT", "SL_HIT", "EXPIRED"
    closed_price: Optional[float] = None  # optional, auto-derived from TP/SL if not given


def _calc_points(market: str, price_diff: float) -> float:
    """
    Unified pip/points per market:
    Metals  ×10   → $0.1 move = 1 pt  (XAUUSD $47 move = 470 pts)
    Crypto  ×1    → $1   move = 1 pt  (BTC $500 move = 500 pts)
    Indices ×1    → 1 index point = 1 pt (NAS100 +40 = 40 pts)
    Oil/Gas ×10   → $0.1 move = 1 pt
    JPY     ×100  → standard yen pips
    Forex   ×10000→ standard pips (0.0001 = 1 pip)
    """
    symbol = (market or "").upper()
    if symbol in ("XAUUSD", "XAGUSD", "XPTUSD", "XPDUSD"):
        return round(price_diff * 10, 2)     # metals: $0.1 per point
    elif symbol in ("BTCUSD", "ETHUSD", "BNBUSD", "SOLUSD", "XRPUSD"):
        return round(price_diff * 1.0, 2)    # crypto: $1 per point
    elif symbol in ("NAS100", "US30", "SP500", "US100", "NASDAQ", "DOW"):
        return round(price_diff * 1.0, 2)    # indices: 1 index point = 1 pt
    elif symbol in ("USOIL", "OIL", "NATGAS", "BRENT"):
        return round(price_diff * 10, 2)     # oil/gas: $0.1 per point
    elif symbol.endswith("JPY"):
        return round(price_diff * 100, 2)    # yen pairs
    else:
        return round(price_diff * 10000, 2)  # standard forex


@router.get("/signals")
def admin_list_signals(
    status: str = "all",
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """قائمة كل الإشارات للأدمن"""
    q = db.query(Signal)
    if status != "all":
        try:
            q = q.filter(Signal.status == SignalStatus(status))
        except ValueError:
            pass
    total = q.count()
    signals = q.order_by(Signal.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "signals": [_signal_info(s) for s in signals],
    }


@router.patch("/signals/{signal_id}/outcome")
def set_signal_outcome(
    signal_id: int,
    data: SignalOutcomeIn,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """تحديد نتيجة إشارة (TP1/TP2/SL/EXPIRED)"""
    signal = db.query(Signal).filter(Signal.id == signal_id).first()
    if not signal:
        raise HTTPException(404, "الإشارة غير موجودة")

    valid_statuses = {"TP1_HIT", "TP2_HIT", "SL_HIT", "EXPIRED"}
    if data.status not in valid_statuses:
        raise HTTPException(400, f"الحالة يجب أن تكون إحدى: {valid_statuses}")

    entry = signal.entry_price
    sl    = signal.stop_loss
    tp1   = signal.take_profit_1
    tp2   = signal.take_profit_2
    is_buy = (signal.signal_type.value if hasattr(signal.signal_type, 'value') else signal.signal_type) == "BUY"

    if data.status == "TP1_HIT":
        exit_price = data.closed_price or tp1
        diff = abs(tp1 - entry)
        # For BUY: tp1 > entry so positive; for SELL: entry > tp1 so positive too
        pts = _calc_points(signal.market, diff)
        if not is_buy:
            diff = abs(entry - tp1)
            pts = _calc_points(signal.market, diff)
        points = pts

    elif data.status == "TP2_HIT":
        exit_price = data.closed_price or tp2
        diff = abs(tp2 - entry)
        points = _calc_points(signal.market, diff)

    elif data.status == "SL_HIT":
        exit_price = data.closed_price or sl
        diff = abs(entry - sl)
        points = -_calc_points(signal.market, diff)

    else:  # EXPIRED
        exit_price = data.closed_price or entry
        points = 0.0

    try:
        signal.status       = SignalStatus(data.status)
    except ValueError:
        raise HTTPException(400, f"حالة غير صحيحة: {data.status}")

    # نسبة الربح/الخسارة المئوية بناءً على سعر الدخول
    if entry and entry > 0:
        if is_buy:
            pnl_pct = round((exit_price - entry) / entry * 100, 3)
        else:
            pnl_pct = round((entry - exit_price) / entry * 100, 3)
    else:
        pnl_pct = 0.0

    signal.points_earned            = round(points, 2)
    signal.profit_loss              = round(points, 2)
    signal.profit_loss_percentage   = pnl_pct
    signal.exit_executed            = datetime.now(timezone.utc)

    db.commit()
    db.refresh(signal)
    logger.info(f"Signal {signal_id} outcome: {data.status}, points={points:.2f}, pnl%={pnl_pct:.3f}%")
    return {"success": True, "signal": _signal_info(signal)}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _user_info(u: User) -> dict:
    now = datetime.now(timezone.utc)
    days_left = None
    if u.subscription_ends_at:
        delta = u.subscription_ends_at - now
        days_left = max(0, delta.days)
    elif u.trial_ends_at:
        delta = u.trial_ends_at - now
        days_left = max(0, delta.days)
    return {
        "id":            u.id,
        "email":         u.email,
        "full_name":     u.full_name or "",
        "role":          u.role,
        "plan":          u.plan,
        "is_active":     u.is_active,
        "days_left":     days_left,
        "telegram_id":   u.telegram_id,
        "telegram_username": u.telegram_username,
        "trial_analyses_left": u.trial_analyses_left,
        "trial_chat_left":     u.trial_chat_left,
        "analyses_total":      u.analyses_total,
        "chat_total":          u.chat_total,
        "subscription_ends_at": u.subscription_ends_at.isoformat() if u.subscription_ends_at else None,
        "created_at":    u.created_at.isoformat() if u.created_at else None,
        "last_seen_at":  u.last_seen_at.isoformat() if u.last_seen_at else None,
    }


def _payment_info(p: Payment) -> dict:
    return {
        "id":         p.id,
        "user_id":    p.user_id,
        "plan":       p.plan,
        "amount_usd": p.amount_usd,
        "network":    p.network,
        "tx_id":      p.tx_id,
        "status":     p.status,
        "admin_note": p.admin_note,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def _payment_full(p: Payment, db: Session) -> dict:
    info = _payment_info(p)
    user = db.query(User).filter(User.id == p.user_id).first()
    if user:
        info["user_email"] = user.email
        info["user_name"]  = user.full_name or ""
    return info


def _market_info(m: MarketConfig) -> dict:
    return {
        "symbol":       m.symbol,
        "display_name": m.display_name,
        "category":     m.category,
        "is_active":    m.is_active,
        "is_premium":   m.is_premium,
        "yf_symbol":    m.yf_symbol,
        "td_symbol":    m.td_symbol,
        "sort_order":   m.sort_order,
    }


def _signal_info(s: Signal) -> dict:
    return {
        "id":            s.id,
        "user_id":       s.user_id,
        "market":        s.market,
        "signal_type":   s.signal_type.value if hasattr(s.signal_type, 'value') else s.signal_type,
        "status":        s.status.value if hasattr(s.status, 'value') else s.status,
        "entry_price":   s.entry_price,
        "stop_loss":     s.stop_loss,
        "take_profit_1": s.take_profit_1,
        "take_profit_2": s.take_profit_2,
        "points_earned": s.points_earned,
        "profit_loss":   s.profit_loss,
        "ai_confidence": s.ai_confidence,
        "created_at":    s.created_at.isoformat() if s.created_at else None,
        "exit_executed": s.exit_executed.isoformat() if s.exit_executed else None,
    }


# ─── Performance Report ───────────────────────────────────────────────────────

class ReportSendIn(BaseModel):
    days: int = 7           # عدد الأيام للتقرير (7=أسبوع، 1=يوم، 30=شهر)
    channel: str = "telegram"  # "telegram" أو "email"
    include_expired: bool = True  # يشمل المستخدمين منتهي الاشتراك


def _build_performance_report(signals: list, days: int) -> tuple[str, str]:
    """
    يبني تقرير الأداء — يُعيد (telegram_text, email_html)
    """
    closed   = [s for s in signals if s.status.value in ("TP1_HIT", "TP2_HIT", "SL_HIT")]
    wins     = [s for s in closed if s.status.value in ("TP1_HIT", "TP2_HIT")]
    losses   = [s for s in closed if s.status.value == "SL_HIT"]
    total_pts= sum(s.points_earned or 0 for s in closed)
    win_rate = round(len(wins) / len(closed) * 100) if closed else 0
    period   = "اليوم" if days == 1 else f"آخر {days} يوم" if days < 30 else "الشهر"

    # ── Telegram (HTML) ──────────────────────────────────────────────────────
    pts_sign = "+" if total_pts >= 0 else ""
    tg_lines = [
        f"📊 <b>تقرير أداء Qaffel AI</b>",
        f"🗓 الفترة: {period}",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"📈 إجمالي الصفقات: <b>{len(closed)}</b>",
        f"✅ رابحة: <b>{len(wins)}</b>  │  ❌ خاسرة: <b>{len(losses)}</b>",
        f"🏆 نسبة الربح: <b>{win_rate}%</b>",
        f"⚡ إجمالي النقاط: <b>{pts_sign}{total_pts:.1f}</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
    ]

    if closed:
        tg_lines.append("📋 <b>الصفقات:</b>")
        for s in closed[:10]:  # أقصى 10
            st    = s.status.value
            icon  = "✅" if st in ("TP1_HIT", "TP2_HIT") else "❌"
            tp    = "TP2" if st == "TP2_HIT" else "TP1" if st == "TP1_HIT" else "SL"
            pts   = s.points_earned or 0
            sign  = "+" if pts >= 0 else ""
            stype = "شراء" if (s.signal_type.value if hasattr(s.signal_type,"value") else s.signal_type) == "BUY" else "بيع"
            tg_lines.append(
                f"{icon} {s.market} {stype} — {tp}  <code>{sign}{pts:.1f} نقطة</code>"
            )
        if len(closed) > 10:
            tg_lines.append(f"<i>... و {len(closed)-10} صفقة أخرى</i>")

    tg_lines += [
        "━━━━━━━━━━━━━━━━━━━━━━",
        "🤖 <i>Qaffel AI — التداول الذكي</i>",
    ]
    tg_text = "\n".join(tg_lines)

    # ── Email (HTML) ─────────────────────────────────────────────────────────
    rows = ""
    for s in closed:
        st    = s.status.value
        color = "#22c55e" if st in ("TP1_HIT","TP2_HIT") else "#ef4444"
        tp    = "TP2" if st=="TP2_HIT" else "TP1" if st=="TP1_HIT" else "SL"
        pts   = s.points_earned or 0
        sign  = "+" if pts >= 0 else ""
        stype = "شراء" if (s.signal_type.value if hasattr(s.signal_type,"value") else s.signal_type) == "BUY" else "بيع"
        date  = s.exit_executed.strftime("%d/%m") if s.exit_executed else "—"
        rows += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #1f2937">{s.market}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #1f2937">{stype}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #1f2937;color:{color};font-weight:bold">{tp}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #1f2937;color:{color};font-weight:bold">{sign}{pts:.1f}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #1f2937;color:#9ca3af">{date}</td>
        </tr>"""

    email_html = f"""
    <div style="background:#111827;color:#f9fafb;font-family:Arial,sans-serif;max-width:600px;margin:auto;border-radius:12px;overflow:hidden">
      <div style="background:#1e40af;padding:24px;text-align:center">
        <h1 style="margin:0;font-size:22px">📊 تقرير أداء Qaffel AI</h1>
        <p style="margin:6px 0 0;opacity:.8">الفترة: {period}</p>
      </div>
      <div style="padding:24px">
        <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px">
          <div style="flex:1;background:#1f2937;border-radius:8px;padding:16px;text-align:center;min-width:100px">
            <div style="font-size:28px;font-weight:bold">{len(closed)}</div>
            <div style="color:#9ca3af;font-size:12px">إجمالي الصفقات</div>
          </div>
          <div style="flex:1;background:#1f2937;border-radius:8px;padding:16px;text-align:center;min-width:100px">
            <div style="font-size:28px;font-weight:bold;color:#22c55e">{win_rate}%</div>
            <div style="color:#9ca3af;font-size:12px">نسبة الربح</div>
          </div>
          <div style="flex:1;background:#1f2937;border-radius:8px;padding:16px;text-align:center;min-width:100px">
            <div style="font-size:28px;font-weight:bold;color:{'#22c55e' if total_pts>=0 else '#ef4444'}">{pts_sign}{total_pts:.1f}</div>
            <div style="color:#9ca3af;font-size:12px">إجمالي النقاط</div>
          </div>
        </div>
        {"<table style='width:100%;border-collapse:collapse;direction:rtl'><thead><tr style='background:#1f2937'><th style='padding:10px 12px;text-align:right'>الزوج</th><th style='padding:10px 12px;text-align:right'>النوع</th><th style='padding:10px 12px;text-align:right'>النتيجة</th><th style='padding:10px 12px;text-align:right'>النقاط</th><th style='padding:10px 12px;text-align:right'>التاريخ</th></tr></thead><tbody>" + rows + "</tbody></table>" if rows else "<p style='color:#9ca3af;text-align:center'>لا توجد صفقات مغلقة في هذه الفترة</p>"}
      </div>
      <div style="background:#1f2937;padding:16px;text-align:center;color:#6b7280;font-size:12px">
        Qaffel AI — التداول الذكي بالذكاء الاصطناعي
      </div>
    </div>"""

    return tg_text, email_html


@router.get("/performance-report")
def get_performance_report(
    days: int = Query(default=7, ge=1, le=90),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """جلب بيانات تقرير الأداء للمعاينة قبل الإرسال"""
    from datetime import date as dt_date, time as dt_time
    now       = datetime.now(timezone.utc)
    start_dt  = now - timedelta(days=days)
    closed    = [SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT]

    signals = (
        db.query(Signal)
        .filter(Signal.status.in_(closed), Signal.exit_executed >= start_dt)
        .order_by(Signal.exit_executed.desc())
        .all()
    )

    wins    = [s for s in signals if s.status.value in ("TP1_HIT","TP2_HIT")]
    losses  = [s for s in signals if s.status.value == "SL_HIT"]
    pts     = sum(s.points_earned or 0 for s in signals)

    return {
        "days":       days,
        "total":      len(signals),
        "wins":       len(wins),
        "losses":     len(losses),
        "win_rate":   round(len(wins)/len(signals)*100) if signals else 0,
        "total_points": round(pts, 2),
        "signals": [
            {
                "market":       s.market,
                "signal_type":  s.signal_type.value if hasattr(s.signal_type,"value") else s.signal_type,
                "status":       s.status.value if hasattr(s.status,"value") else s.status,
                "points":       round(s.points_earned or 0, 2),
                "entry_price":  s.entry_price,
                "ai_confidence":s.ai_confidence,
                "exit_date":    s.exit_executed.strftime("%d/%m %H:%M") if s.exit_executed else None,
            }
            for s in signals
        ],
    }


@router.post("/performance-report/send")
def send_performance_report(
    data: ReportSendIn,
    background: BackgroundTasks,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """إرسال تقرير الأداء لكل المستخدمين عبر تيليجرام أو إيميل"""
    now      = datetime.now(timezone.utc)
    start_dt = now - timedelta(days=data.days)
    closed   = [SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT]

    signals  = (
        db.query(Signal)
        .filter(Signal.status.in_(closed), Signal.exit_executed >= start_dt)
        .order_by(Signal.exit_executed.desc())
        .all()
    )

    tg_text, email_html = _build_performance_report(signals, data.days)
    period = "اليوم" if data.days == 1 else f"آخر {data.days} يوم" if data.days < 30 else "الشهر"

    # ── جمع المستلمين ────────────────────────────────────────────────────────
    q = db.query(User).filter(User.is_active == True, User.plan != PlanType.BANNED)
    users = q.all()

    if data.channel == "telegram":
        if not _settings.TELEGRAM_BOT_TOKEN:
            raise HTTPException(400, "TELEGRAM_BOT_TOKEN غير مضبوط")
        tg_users = [u for u in users if u.telegram_id]
        if not tg_users:
            return {"message": "لا يوجد مستخدمون لديهم تيليجرام", "sent": 0}

        def _tg_broadcast():
            import time as _t
            sent = 0
            for u in tg_users:
                ok = _send_telegram_message(u.telegram_id, tg_text)
                if ok:
                    sent += 1
                _t.sleep(0.05)
            logger.info(f"📊 Performance report sent to {sent}/{len(tg_users)} Telegram users")

        background.add_task(_tg_broadcast)
        return {"message": f"⏳ جاري إرسال تقرير '{period}' لـ {len(tg_users)} مستخدم تيليجرام", "sent": len(tg_users)}

    else:  # email
        if not _settings.SMTP_PASSWORD:
            raise HTTPException(400, "SMTP غير مضبوط")
        email_users = [u for u in users if u.email]
        subject     = f"📊 تقرير أداء Qaffel AI — {period}"

        def _email_broadcast():
            import time as _t
            sent = 0
            for u in email_users:
                try:
                    _send_email_svc(u.email, subject, email_html, _settings.SMTP_PASSWORD)
                    sent += 1
                    _t.sleep(0.1)
                except Exception as _e:
                    logger.warning(f"email report to {u.email}: {_e}")
            logger.info(f"📊 Performance report emailed to {sent}/{len(email_users)} users")

        background.add_task(_email_broadcast)
        return {"message": f"⏳ جاري إرسال تقرير '{period}' لـ {len(email_users)} مستخدم بالإيميل", "sent": len(email_users)}


# ─── Admin Affiliate ───────────────────────────────────────────────────────────

class PayoutIn(BaseModel):
    amount_usd: float
    note: str = ""


@router.get("/affiliate/stats")
def admin_affiliate_stats(
    skip: int = 0,
    limit: int = 50,
    search: str = "",
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """قائمة كل المسوّقين"""
    q = db.query(Affiliate).join(User, Affiliate.user_id == User.id)
    if search:
        q = q.filter((User.email.ilike(f"%{search}%")) | (Affiliate.code.ilike(f"%{search}%")))
    total = q.count()
    affiliates = q.order_by(Affiliate.pending_balance_usd.desc()).offset(skip).limit(limit).all()
    result = []
    for a in affiliates:
        tier = 2 if a.total_referrals >= TIER2_THRESHOLD else 1
        result.append({
            "affiliate_id":        a.id,
            "user_id":             a.user_id,
            "user_email":          a.user.email if a.user else "",
            "code":                a.code,
            "total_referrals":     a.total_referrals,
            "current_tier":        tier,
            "commission_rate_pct": 15 if tier == 2 else 5,
            "pending_balance_usd": a.pending_balance_usd,
            "paid_out_usd":        a.paid_out_usd,
        })
    return {"total": total, "affiliates": result}


@router.get("/affiliate/{affiliate_id}/referrals")
def admin_affiliate_referrals(
    affiliate_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """تفاصيل إحالات مسوّق معين"""
    rows = db.query(AffiliateReferral).filter(
        AffiliateReferral.affiliate_id == affiliate_id
    ).order_by(AffiliateReferral.created_at.desc()).all()
    return [
        {
            "id":                  r.id,
            "referred_user_email": r.referred_user.email if r.referred_user else "",
            "payment_amount_usd":  r.payment_amount_usd,
            "commission_usd":      r.commission_usd,
            "commission_rate_pct": int(r.commission_rate * 100),
            "tier":                r.tier,
            "created_at":          r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.post("/affiliate/{affiliate_id}/payout")
def admin_affiliate_payout(
    affiliate_id: int,
    data: PayoutIn,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """تسجيل دفعة للمسوّق"""
    aff = db.query(Affiliate).filter(Affiliate.id == affiliate_id).first()
    if not aff:
        raise HTTPException(404, "المسوّق غير موجود")
    if data.amount_usd <= 0:
        raise HTTPException(400, "المبلغ يجب أن يكون أكبر من صفر")
    if data.amount_usd > aff.pending_balance_usd:
        raise HTTPException(400, f"الرصيد المتاح {aff.pending_balance_usd:.2f}$ فقط")
    # Check minimum payout setting
    min_payout_row = db.query(SiteSettings).filter(SiteSettings.key == "affiliate_min_payout_usd").first()
    min_payout = float(min_payout_row.value) if min_payout_row and min_payout_row.value else 10.0
    if data.amount_usd < min_payout:
        raise HTTPException(400, f"الحد الأدنى للسحب هو ${min_payout:.2f}")
    aff.pending_balance_usd = round(aff.pending_balance_usd - data.amount_usd, 4)
    aff.paid_out_usd        = round(aff.paid_out_usd + data.amount_usd, 4)
    db.commit()
    logger.info(f"💸 Payout: affiliate_id={affiliate_id} amount={data.amount_usd}$ note={data.note}")
    return {
        "success":             True,
        "pending_balance_usd": aff.pending_balance_usd,
        "paid_out_usd":        aff.paid_out_usd,
    }
