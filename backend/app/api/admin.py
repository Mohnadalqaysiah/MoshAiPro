"""
Mosh AI Pro v5 - Admin API
Full control: Users, Payments, Markets
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
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
from app.services.subscription_service import activate_subscription_payment
from app.config import get_settings

_settings = get_settings()

router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────────────────────────

class RoleUpdateIn(BaseModel):
    role: str   # "admin" | "user"


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

    # عدّاد الحسابات المشتركة بنفس IP التسجيل (لكشف تعدد الحسابات)
    dup_counts = dict(
        db.query(User.registration_ip, func.count(User.id))
        .filter(User.registration_ip.isnot(None))
        .group_by(User.registration_ip)
        .having(func.count(User.id) > 1)
        .all()
    )

    infos = []
    for u in users:
        info = _user_info(u)
        info["dup_ip_count"] = dup_counts.get(u.registration_ip, 1) if u.registration_ip else 0
        infos.append(info)

    now = datetime.now(timezone.utc)
    online_count = db.query(User).filter(
        User.last_seen_at.isnot(None),
        User.last_seen_at > now - timedelta(seconds=_ONLINE_WINDOW_SEC),
    ).count()

    return {"total": total, "users": infos, "online_count": online_count}


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


# ─── Team (Admin/Manager access) ───────────────────────────────────────────────

@router.get("/team")
def list_team(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """كل حسابات الإدارة الحالية — لقسم 'الفريق' بلوحة الإدارة."""
    admins = db.query(User).filter(User.role == UserRole.ADMIN).order_by(User.created_at.asc()).all()
    return {"admins": [_user_info(u) for u in admins]}


@router.post("/users/{user_id}/set-role")
def set_user_role(
    user_id: int,
    data: RoleUpdateIn,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """ترقية مستخدم لأدمن أو إلغاء صلاحياته — صلاحية موحّدة (لا مستويات حالياً)."""
    try:
        new_role = UserRole(data.role)
    except ValueError:
        raise HTTPException(400, f"دور غير صحيح: {data.role}")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "المستخدم غير موجود")

    if new_role == UserRole.USER:
        if user.id == admin.id:
            raise HTTPException(400, "لا يمكنك إلغاء صلاحياتك الخاصة")
        remaining_admins = db.query(User).filter(
            User.role == UserRole.ADMIN, User.id != user_id
        ).count()
        if user.role == UserRole.ADMIN and remaining_admins == 0:
            raise HTTPException(400, "لا يمكن إزالة آخر حساب أدمن بالمنصة")

    user.role = new_role
    db.commit()
    logger.info(f"🔑 Admin {admin.email} set role of {user.email} → {new_role.value}")
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


class BulkResetTrialIn(BaseModel):
    notify_telegram: bool = False


@router.post("/users/bulk-reset-trial")
def bulk_reset_trial(
    data: BulkResetTrialIn,
    background: BackgroundTasks,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """إعادة تعيين كريدت التجربة لجميع المستخدمين التجريبيين دفعة واحدة"""
    def _get_int(key: str, default: int) -> int:
        r = db.query(SiteSettings).filter(SiteSettings.key == key).first()
        try: return int(r.value) if r and r.value else default
        except: return default

    analysis_limit = _get_int("trial_analysis_limit", 10)
    chat_limit     = _get_int("trial_chat_limit", 20)
    now = datetime.now(timezone.utc)

    trial_users = db.query(User).filter(User.plan == PlanType.TRIAL).all()
    count = notified = 0

    for user in trial_users:
        user.trial_analyses_left = analysis_limit
        user.trial_chat_left     = chat_limit
        user.trial_started_at    = now
        user.trial_ends_at       = now + timedelta(days=7)
        user.is_active           = True
        count += 1
        if data.notify_telegram and user.telegram_id:
            msg = (
                f"🎁 <b>تم تجديد حسابك التجريبي!</b>\n\n"
                f"التحليلات المتاحة: <b>{analysis_limit}</b>\n"
                f"المحادثات المتاحة: <b>{chat_limit}</b>"
            )
            background.add_task(_send_telegram_message, user.telegram_id, msg)
            notified += 1

    db.commit()
    logger.info(f"🔄 Bulk trial reset: {count} users, notified: {notified}")
    return {
        "success":        True,
        "reset":          count,
        "notified":       notified,
        "analysis_limit": analysis_limit,
        "chat_limit":     chat_limit,
    }


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

    if data.action == "approve":
        payment.status      = PaymentStatus.APPROVED
        payment.admin_note  = data.admin_note
        payment.approved_by = admin.id
        activate_subscription_payment(db, payment, background)

    elif data.action == "reject":
        payment.status     = PaymentStatus.REJECTED
        payment.admin_note = data.admin_note
        logger.info(f"❌ Payment rejected: id={payment_id}")
    else:
        raise HTTPException(400, "action يجب أن يكون approve أو reject")

    db.commit()

    # ── إيميل رفض للمستخدم بعد الـ commit (إيميل القبول تُرسل داخل activate_subscription_payment) ──
    if data.action == "reject" and _settings.SMTP_PASSWORD:
        from app.services.email_service import send_email, payment_rejected_email_body
        _user = db.query(User).filter(User.id == payment.user_id).first()
        if _user:
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

def _get_bot_token(db: Session) -> str:
    """Returns bot token: DB override first, then env var."""
    row = db.query(SiteSettings).filter(SiteSettings.key == "telegram_bot_token").first()
    if row and row.value and row.value.strip():
        return row.value.strip()
    return _settings.TELEGRAM_BOT_TOKEN or ""


def _send_telegram_message(chat_id: str, text: str, db: Session = None) -> bool:
    """إرسال رسالة تيليجرام واحدة"""
    token = _get_bot_token(db) if db else (_settings.TELEGRAM_BOT_TOKEN or "")
    if not token:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
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
    if not _get_bot_token(db):
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
        sent = sum(1 for cid in chat_ids if _send_telegram_message(cid, text, db))
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
    Gulf    ×10   → نفس مقياس المعادن (أسهم بأسعار مشابهة النطاق: عشرات الريال/الدرهم)
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
    elif symbol in ("ARAMCO", "RAJHI", "SABIC", "STC", "TASI", "SNB", "MAADEN", "ALMARAI",
                     "BAHRI", "ALINMA", "EMAAR", "DFMGI", "EMIRATESNBD", "DIB",
                     "FAB", "ADNOCDIST", "QNBK"):
        return round(price_diff * 10, 2)     # أسهم خليجية: 0.1 ريال/درهم لكل نقطة
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
    from sqlalchemy.orm import joinedload
    q = db.query(Signal).options(joinedload(Signal.user))
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

_ONLINE_WINDOW_SEC = 300   # نفس نافذة "متصل الآن" بكل مكان بالإدارة — 5 دقائق


def _is_online(u: User, now: datetime) -> bool:
    if not u.last_seen_at:
        return False
    last_seen = u.last_seen_at
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    return (now - last_seen).total_seconds() < _ONLINE_WINDOW_SEC


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
        "is_verified":   u.is_verified,
        "registration_ip": u.registration_ip,
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
        "is_online":     _is_online(u, now),
    }


def _payment_info(p: Payment) -> dict:
    return {
        "id":         p.id,
        "user_id":    p.user_id,
        "plan":       p.plan,
        "amount_usd": p.amount_usd,
        "network":    p.network,
        "provider":   p.provider,
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
    user_email = s.user.email if hasattr(s, 'user') and s.user else None
    return {
        "id":            s.id,
        "user_id":       s.user_id,
        "user_email":    user_email,
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
        if not _get_bot_token(db):
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


# ─── Re-engagement Campaign ───────────────────────────────────────────────────

class ReEngageCampaignIn(BaseModel):
    message:           str                   # نص الرسالة (يدعم {name})
    interval_days:     int   = 3             # كم يوم بين كل إرسال
    max_sends:         int   = 3             # الحد الأقصى للإرسال لكل مستخدم
    expired_since_days: int  = 0             # المنتهيون منذ X يوم فقط (0=الكل)
    include_trial:     bool  = False         # هل يشمل التجريبيين المنتهيين
    dry_run:           bool  = False         # معاينة فقط بدون إرسال


class ReEngageCampaignScheduleIn(BaseModel):
    message:           str
    interval_days:     int  = 3
    max_sends:         int  = 3
    include_trial:     bool = False


@router.get("/reengagement/preview")
def reengagement_preview(
    expired_since_days: int = 0,
    include_trial: bool = False,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """معاينة قائمة المستخدمين المنتهيين الذين لديهم Telegram"""
    now = datetime.now(timezone.utc)

    q = db.query(User).filter(
        User.telegram_id != None,  # noqa
        User.telegram_id != "",
    )

    if include_trial:
        q = q.filter(User.plan.in_([PlanType.WEEKLY, PlanType.MONTHLY, PlanType.TRIAL]))
    else:
        q = q.filter(User.plan.in_([PlanType.WEEKLY, PlanType.MONTHLY]))

    # منتهيو الاشتراك
    q = q.filter(
        (User.subscription_ends_at < now) | (User.subscription_ends_at == None)  # noqa
    )

    if expired_since_days > 0:
        cutoff = now - timedelta(days=expired_since_days)
        q = q.filter(User.subscription_ends_at >= cutoff)

    users = q.all()
    return {
        "count": len(users),
        "users": [
            {
                "id":          u.id,
                "name":        u.full_name or u.email.split("@")[0],
                "email":       u.email,
                "plan":        u.plan.value,
                "telegram_id": u.telegram_id,
                "expired_at":  u.subscription_ends_at.isoformat() if u.subscription_ends_at else None,
            }
            for u in users[:50]   # أول 50 للمعاينة
        ],
    }


@router.post("/reengagement/send")
def reengagement_send(
    data: ReEngageCampaignIn,
    background: BackgroundTasks,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """
    إرسال رسالة دعائية للمستخدمين المنتهيين عبر تيليجرام.
    يدعم {name} في نص الرسالة.
    interval_days / max_sends: للتتبع في SiteSettings (re_engage_log).
    """
    now = datetime.now(timezone.utc)

    q = db.query(User).filter(
        User.telegram_id != None,  # noqa
        User.telegram_id != "",
        (User.subscription_ends_at < now) | (User.subscription_ends_at == None),  # noqa
    )
    if not data.include_trial:
        q = q.filter(User.plan.in_([PlanType.WEEKLY, PlanType.MONTHLY]))
    else:
        q = q.filter(User.plan.in_([PlanType.WEEKLY, PlanType.MONTHLY, PlanType.TRIAL]))

    if data.expired_since_days > 0:
        cutoff = now - timedelta(days=data.expired_since_days)
        q = q.filter(User.subscription_ends_at >= cutoff)

    users = q.all()

    if not users:
        return {"success": True, "sent": 0, "message": "لا يوجد مستخدمون مؤهلون"}

    if data.dry_run:
        return {
            "success": True,
            "dry_run": True,
            "would_send": len(users),
            "sample": [u.email for u in users[:5]],
        }

    # بناء قائمة (chat_id, text) مخصصة
    import json as _json
    tasks: list[tuple[str, str]] = []
    for u in users:
        name = u.full_name or u.email.split("@")[0]
        text = data.message.replace("{name}", name)
        tasks.append((u.telegram_id, text))

    def _campaign_task(tasks_list):
        import time as _t
        sent = 0
        for cid, txt in tasks_list:
            if _send_telegram_message(cid, txt):
                sent += 1
            _t.sleep(0.05)
        logger.info(f"📣 Re-engagement campaign: sent={sent}/{len(tasks_list)}")

    background.add_task(_campaign_task, tasks)

    logger.info(
        f"📣 Re-engagement campaign queued: users={len(users)} "
        f"interval={data.interval_days}d max={data.max_sends}"
    )
    return {
        "success":   True,
        "queued":    len(users),
        "message":   f"جاري إرسال {len(users)} رسالة في الخلفية",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM DIAGNOSTIC MODE
# ═══════════════════════════════════════════════════════════════════════════════

_DIAG_SYMBOLS = [
    "XAUUSD", "XAGUSD", "BTCUSD", "ETHUSD",
    "EURUSD", "GBPUSD", "USDJPY",
    "NAS100", "US30", "USOIL",
]
_DIAG_TIMEFRAME = "1h"


@router.get("/diagnostic")
async def system_diagnostic(
    admin: User = Depends(get_admin_user),
):
    """
    Full System Diagnostic Mode.
    Steps 1-8: market state, pipeline trace, rejection analysis,
    threshold stress test, cooldown check, calibration status, diagnosis, plan.
    """
    import time as _t
    import asyncio

    from app.services.ai_engine_v5 import mosh_ai_engine_v5 as _engine
    from app.services.ict_engine import ict_engine as _ict
    from app.services.smart_data import smart_data as _sd

    started = _t.time()
    results = {}

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 1 — Market Activity Check
    # ─────────────────────────────────────────────────────────────────────────
    step1 = {}
    active_markets = 0

    for sym in _DIAG_SYMBOLS:
        try:
            df = await _sd.get_ohlcv(sym, _DIAG_TIMEFRAME, bars=80)
            if df is None or len(df) < 30:
                step1[sym] = {"error": "no_data"}
                continue

            ict = _ict.full_analysis(df, sym, _DIAG_TIMEFRAME)

            struct    = ict.get("market_structure", {})
            sweep     = ict.get("liquidity_sweep", {})
            mm        = ict.get("market_mode", {})
            bos_list  = struct.get("bos_events", [])
            bull_bos  = sum(1 for b in bos_list if "BULLISH" in b.get("type",""))
            bear_bos  = sum(1 for b in bos_list if "BEARISH" in b.get("type",""))
            trend     = struct.get("trend", "RANGING")
            mode      = mm.get("mode", "UNKNOWN")

            # count sweeps in last 20 candles
            sweep_count = int(sweep.get("has_bullish_sweep", False)) + int(sweep.get("has_bearish_sweep", False))

            # breakout attempts — candles closing beyond recent high/low
            closes   = df["close"].values[-10:]
            highs    = df["high"].values[-30:-10]
            lows     = df["low"].values[-30:-10]
            recent_h = float(highs.max()) if len(highs) else 0
            recent_l = float(lows.min())  if len(lows)  else 0
            breakouts = sum(1 for c in closes if c > recent_h or c < recent_l)

            market_state = "RANGING"
            if mode in ("VOLATILE","BREAKOUT") or breakouts >= 3:
                market_state = "VOLATILE"
            elif trend in ("BULLISH","BEARISH") or mode in ("TRENDING","TREND"):
                market_state = "TRENDING"
            if mm.get("in_range_trap") or ict.get("range_conflict",{}).get("in_range_trap"):
                market_state = "TRAP"

            # volatility from ATR%
            lvls    = ict.get("levels", {})
            atr     = float(lvls.get("atr") or 0)
            price   = float(df["close"].iloc[-1])
            atr_pct = atr / price if price else 0
            vol     = "LOW" if atr_pct < 0.003 else ("HIGH" if atr_pct > 0.010 else "NORMAL")

            if market_state in ("TRENDING", "VOLATILE"):
                active_markets += 1

            step1[sym] = {
                "market_state":     market_state,
                "volatility":       vol,
                "trend":            trend,
                "mode":             mode,
                "bos_bull":         bull_bos,
                "bos_bear":         bear_bos,
                "sweep_detected":   sweep_count,
                "breakout_attempts": breakouts,
                "atr_pct":          round(atr_pct * 100, 3),
            }
        except Exception as e:
            step1[sym] = {"error": str(e)}

    global_state = "DEAD_MARKET" if active_markets == 0 else "ACTIVE"
    results["step1_market_activity"] = {
        "symbols":            step1,
        "active_markets":     active_markets,
        "total":              len(_DIAG_SYMBOLS),
        "market_global_state": global_state,
    }

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 2 + 3 — Pipeline Trace & Rejection Analysis
    # ─────────────────────────────────────────────────────────────────────────
    pipeline_traces = []
    rejection_counts: dict = {}
    delta_samples   = []
    rr_samples      = []
    _pre_rescue_cache: dict = {}   # sym -> (ict, htf_ict, ict_dec) — reused by step4's HTF stress test

    for sym in _DIAG_SYMBOLS:
        sym_data = step1.get(sym, {})
        if "error" in sym_data:
            continue
        try:
            df = await _sd.get_ohlcv(sym, _DIAG_TIMEFRAME, bars=150)
            df_htf = await _sd.get_ohlcv(sym, "4h", bars=100)
            if df is None or len(df) < 30:
                continue

            ict     = _ict.full_analysis(df, sym, _DIAG_TIMEFRAME)
            htf_ict = _ict.full_analysis(df_htf, sym, "4h") if df_htf is not None and len(df_htf) >= 30 else None

            # Run calibration + decision finalizer — PRE-RESCUE reference only,
            # used for the delta/threshold breakdown below and by step4's HTF
            # stress test. This is NOT what users actually receive — see
            # `real_decision` below for that.
            ict   = _engine._auto_calibrate_thresholds(ict, sym, _DIAG_TIMEFRAME)
            calib = ict.get("calibration_params", {})
            ict_dec = _engine._decision_finalizer(ict.copy(), sym, _DIAG_TIMEFRAME, htf_ict)
            _pre_rescue_cache[sym] = (ict, htf_ict, ict_dec)

            pre_rescue_decision = ict_dec.get("recommendation", "WAIT")
            pre_rescue_reason   = ict_dec.get("rejection_reason") or ict_dec.get("no_trade_reason", "")

            conf   = ict.get("confluence", {})
            bull_s = float(conf.get("bull_score", 0))
            bear_s = float(conf.get("bear_score", 0))
            delta  = abs(bull_s - bear_s)
            req_d  = calib.get("delta", 20)
            min_rr = calib.get("min_rr", 1.4)

            # ── REAL decision — full analyze_market() pipeline, same path
            # bot.py / strategy_checker actually use. Includes
            # _smart_rescue_layer / _borderline_rescue_layer, which the old
            # diagnostic (calling _decision_finalizer/_institutional_gate
            # directly) skipped entirely — showing a decision users never
            # actually saw. This was a real discrepancy: a symbol could show
            # "REJECTED" here while analyze_market() rescued it back to a
            # live BUY/SELL signal.
            full = await _engine.analyze_market(symbol=sym, timeframe=_DIAG_TIMEFRAME, force_refresh=True)
            decision   = full.get("recommendation", "WAIT")
            rej_reason = full.get("rejection_reason") or full.get("no_trade_reason", "")
            rescued    = bool(full.get("smart_rescued") or full.get("rescued_candidate"))
            rr_val     = float((full.get("levels") or {}).get("risk_reward") or 0)

            rr_samples.append(rr_val or 0)
            delta_samples.append(delta)

            final_status = "PASSED" if decision in ("BUY", "SELL") else "REJECTED"
            trace = {
                "symbol":              sym,
                "timeframe":           _DIAG_TIMEFRAME,
                "decision":            final_status,
                "rescued":             rescued,
                "reason":              rej_reason or "N/A",
                "decision_layer":      full.get("decision_layer", "?"),
                "confluence_factors":  full.get("confluence_factors"),
                "pre_rescue_decision": pre_rescue_decision,
                "pre_rescue_reason":   pre_rescue_reason or "N/A",
                "delta":               round(delta, 1),
                "required_delta":      req_d,
                "rr":                  round(rr_val, 2) if rr_val else None,
                "min_rr":              round(min_rr, 2),
                "market_state":        calib.get("market_state", "?"),
                "calibrated":          bool(ict.get("calibration_params")),
            }
            pipeline_traces.append(trace)

            if final_status == "REJECTED" and rej_reason:
                key = str(rej_reason).split("_")[0:3]
                key = "_".join(key)
                rejection_counts[key] = rejection_counts.get(key, 0) + 1

        except Exception as e:
            pipeline_traces.append({"symbol": sym, "error": str(e)})

    # aggregation
    total_analyzed  = len([t for t in pipeline_traces if "error" not in t])
    total_rejected  = len([t for t in pipeline_traces if t.get("decision") == "REJECTED"])
    total_passed    = total_analyzed - total_rejected
    avg_delta       = round(sum(delta_samples) / len(delta_samples), 1) if delta_samples else 0
    avg_rr          = round(sum(rr_samples) / len(rr_samples), 2)       if rr_samples   else 0
    most_common_rej = max(rejection_counts, key=rejection_counts.get) if rejection_counts else "N/A"
    rej_dist = {
        k: f"{round(v/total_rejected*100,1)}%" if total_rejected else "0%"
        for k,v in sorted(rejection_counts.items(), key=lambda x: -x[1])
    }

    results["step2_pipeline_trace"] = pipeline_traces
    results["step3_rejection_analysis"] = {
        "total_analyzed":            total_analyzed,
        "total_passed":              total_passed,
        "total_rejected":            total_rejected,
        "pass_rate":                 f"{round(total_passed/total_analyzed*100,1)}%" if total_analyzed else "0%",
        "most_common_rejection":     most_common_rej,
        "rejection_distribution":    rej_dist,
        "avg_delta":                 avg_delta,
        "avg_rr":                    avg_rr,
        "required_delta_range":      "20-35",
        "required_rr_range":         "1.2-2.0",
    }

    # ─────────────────────────────────────────────────────────────────────────
    # Decision Layer Breakdown (2026-08-14, Phase 4) — weekly monitoring:
    # is rejection mostly hard vetoes (risk_integrity/htf_veto/zone_veto —
    # healthy, the system is doing its job) or mostly low quality
    # (confluence_insufficient/quality_below_threshold — normal in a quiet
    # market)? A sudden shift in this distribution is a better early signal
    # than pass_rate alone.
    # ─────────────────────────────────────────────────────────────────────────
    layer_counts: dict = {}
    for t in pipeline_traces:
        if "error" in t:
            continue
        layer_counts[t.get("decision_layer", "?")] = layer_counts.get(t.get("decision_layer", "?"), 0) + 1
    results["decision_layer_breakdown"] = {
        "counts": layer_counts,
        "distribution": {
            k: f"{round(v / total_analyzed * 100, 1)}%" if total_analyzed else "0%"
            for k, v in sorted(layer_counts.items(), key=lambda x: -x[1])
        },
        "legend": {
            "risk_integrity":          "RR/SL/TP integrity violation — hard gate, always healthy to see some",
            "htf_veto":                "conflicts with higher-timeframe trend — hard veto",
            "zone_veto":               "wrong side of Premium/Discount zone — hard veto",
            "confluence_insufficient": "direction resolved but <2 of {sweep, structure, OB} confirm it",
            "quality_below_threshold": "score delta / confidence below the bar — plain quiet-market watchlist",
            "passed_all":              "cleared every layer — live BUY/SELL",
        },
    }

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 4 — Threshold Stress Test (simulation only, -5 delta / -0.2 RR)
    # Also stress-tests _DECISION_THRESHOLD_STRONG (the HTF-override
    # threshold, default 40) separately, since HTF_CONFLICT_REJECTED is the
    # most common rejection reason and the base delta/RR relaxation below
    # doesn't touch it at all.
    # ─────────────────────────────────────────────────────────────────────────
    stress_passed = 0
    stress_details = []
    _HTF_STRESS_DELTA = 10   # simulate _DECISION_THRESHOLD_STRONG lowered by this much

    for trace in pipeline_traces:
        if "error" in trace:
            continue
        if trace["decision"] == "PASSED":
            stress_passed += 1
            continue

        # ── HTF-override threshold stress (separate from delta/RR below) ────
        # Pure local re-derivation — does NOT call _decision_finalizer() and
        # does NOT write to _engine._DECISION_THRESHOLD_STRONG (or any other
        # class-level constant) at all, mutable or otherwise. That constant
        # lives on the shared mosh_ai_engine_v5 singleton: a real request
        # (bot_analyze / monitor_watchlists) landing on the same worker
        # process while this endpoint had temporarily lowered it would have
        # seen the relaxed value and could pass an HTF conflict it shouldn't
        # have. Instead we recompute just the two inputs step 6 of
        # _decision_finalizer compares (score_delta magnitude, htf_bias vs.
        # the already-rejected direction) from the cached pre-rescue data and
        # do the same ">=" check ourselves, against a local variable only.
        if str(trace["pre_rescue_reason"]).startswith("HTF_CONFLICT_REJECTED"):
            sym = trace["symbol"]
            cached = _pre_rescue_cache.get(sym)
            if cached:
                ict_c, htf_ict_c, ict_dec_c = cached

                # resolved direction that HTF rejected — _hard_reject() stores
                # it in _pre_reject_rec (set from `analysis["recommendation"]`
                # right before the reject call in _decision_finalizer step 6)
                resolved = ict_dec_c.get("_pre_reject_rec")

                conf_c      = ict_c.get("confluence", {})
                score_delta = abs(float(conf_c.get("bull_score", 0)) - float(conf_c.get("bear_score", 0)))

                htf_trend = str(
                    (htf_ict_c or {}).get("market_structure", {}).get("trend") or "RANGING"
                ).upper()
                htf_bias = "BUY" if htf_trend == "BULLISH" else ("SELL" if htf_trend == "BEARISH" else None)

                current_strong = _engine._DECISION_THRESHOLD_STRONG   # read-only
                relaxed_strong = current_strong - _HTF_STRESS_DELTA

                would_pass_htf = bool(
                    resolved and htf_bias and htf_bias != resolved
                    and score_delta >= relaxed_strong
                )
                if would_pass_htf:
                    stress_passed += 1
                    stress_details.append({
                        "symbol": sym,
                        "reason": trace["reason"],
                        "stress_type": "htf_threshold",
                        "current_strong_threshold": current_strong,
                        "relaxed_strong_threshold": relaxed_strong,
                        "passes_on": "htf_threshold_relaxed",
                    })
                    continue

        # would it pass with relaxed base delta/RR thresholds?
        relaxed_d  = max(trace["required_delta"] - 5, 15)
        relaxed_rr = max((trace["min_rr"] or 1.4) - 0.2, 1.0)
        would_pass_delta = trace["delta"] >= relaxed_d
        would_pass_rr    = (trace["rr"] or 0) >= relaxed_rr if trace["rr"] else False
        if would_pass_delta or would_pass_rr:
            stress_passed += 1
            stress_details.append({
                "symbol": trace["symbol"],
                "reason": trace["reason"],
                "stress_type": "delta_rr",
                "delta":  trace["delta"], "relaxed_delta": relaxed_d,
                "rr":     trace["rr"],    "relaxed_rr":    relaxed_rr,
                "passes_on": "delta" if would_pass_delta else "rr",
            })

    results["step4_stress_test"] = {
        "relaxed_delta":   "required - 5",
        "relaxed_rr":      "min_rr - 0.2",
        "signals_would_pass": stress_passed,
        "total":           total_analyzed,
        "quality_note":    "simulation only — not sent",
        "details":         stress_details,
    }

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 5 — Cooldown Check
    # ─────────────────────────────────────────────────────────────────────────
    import time as _t2
    cooldown_status = []
    blocked_count   = 0
    for sym in _DIAG_SYMBOLS:
        key  = f"{sym.upper()}_{_DIAG_TIMEFRAME}"
        last = _engine._last_signal_time.get(key, 0)
        cd   = _engine._COOLDOWN_SEC.get(_DIAG_TIMEFRAME, 3600)
        elapsed   = int(_t2.time() - last) if last else None
        remaining = max(0, cd - int(_t2.time() - last)) if last else 0
        active    = bool(last and (_t2.time() - last < cd))
        if active:
            blocked_count += 1
        cooldown_status.append({
            "symbol":        sym,
            "timeframe":     _DIAG_TIMEFRAME,
            "cooldown_sec":  cd,
            "last_signal_age_sec": elapsed,
            "remaining_sec": remaining if active else 0,
            "active":        active,
        })
    results["step5_cooldown"] = {
        "items":         cooldown_status,
        "blocked_count": blocked_count,
    }

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 6 — Auto-Calibration Status
    # ─────────────────────────────────────────────────────────────────────────
    calib_summary = []
    for trace in pipeline_traces:
        if "error" not in trace:
            calib_summary.append({
                "symbol":       trace["symbol"],
                "market_state": trace.get("market_state","?"),
                "delta":        trace.get("required_delta"),
                "min_rr":       trace.get("min_rr"),
                "calibrated":   trace.get("calibrated", False),
            })
    results["step6_auto_calibration"] = {
        "engine_winrate":    round(_engine.get_winrate(), 3),
        "perf":              _engine._perf,
        "silence_tracker":   {
            k: f"{round((_t2.time()-v)/3600,1)}h ago"
            for k,v in _engine._last_signal_issued.items()
        },
        "per_symbol": calib_summary,
    }

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 7 — Final Diagnosis
    # ─────────────────────────────────────────────────────────────────────────
    diagnosis = "UNKNOWN"
    diagnosis_reason = ""

    # Check 1: dead market?
    if global_state == "DEAD_MARKET":
        diagnosis = "MARKET SILENCE (VALID)"
        diagnosis_reason = "All symbols ranging/trapped — no BOS or momentum detected"

    # Check 2: cooldown blocking everything?
    elif blocked_count >= len(_DIAG_SYMBOLS) * 0.7:
        diagnosis = "SYSTEM OVER-FILTERING"
        diagnosis_reason = f"Cooldown blocking {blocked_count}/{len(_DIAG_SYMBOLS)} symbols"

    # Check 3: most common rejection is score delta?
    elif most_common_rej and "SCORE" in most_common_rej.upper() and avg_delta < 15:
        diagnosis = "MARKET SILENCE (VALID)"
        diagnosis_reason = f"avg delta={avg_delta} — genuine lack of directional confluence"

    # Check 4: avg delta close to threshold but still failing?
    elif avg_delta >= 12 and total_rejected >= total_analyzed * 0.7:
        diagnosis = "SYSTEM OVER-FILTERING"
        diagnosis_reason = f"avg delta={avg_delta} is close to threshold but {rej_dist} — thresholds may be too strict for current conditions"

    # Check 5: gate rejections dominating?
    elif most_common_rej and any(k in most_common_rej for k in ["RR_","SWEEP","BOS","CONF"]):
        diagnosis = "SYSTEM OVER-FILTERING"
        diagnosis_reason = f"Institutional gate over-filtering: most common = {most_common_rej}"

    # Check 6: stress test shows many would pass
    elif stress_passed > total_analyzed * 0.5 and total_passed == 0:
        diagnosis = "SYSTEM OVER-FILTERING"
        diagnosis_reason = f"{stress_passed}/{total_analyzed} would pass with relaxed thresholds — auto-calibration may need tuning"

    else:
        diagnosis = "MARKET SILENCE (VALID)"
        diagnosis_reason = f"pass_rate={total_passed}/{total_analyzed} — market lacks sufficient confluence"

    results["step7_diagnosis"] = {
        "verdict":        diagnosis,
        "reason":         diagnosis_reason,
        "supporting_data": {
            "global_market_state": global_state,
            "active_markets":      active_markets,
            "pass_rate":           f"{total_passed}/{total_analyzed}",
            "avg_delta":           avg_delta,
            "most_common_rej":     most_common_rej,
            "cooldowns_active":    blocked_count,
            "stress_would_pass":   stress_passed,
        }
    }

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 8 — Action Plan
    # ─────────────────────────────────────────────────────────────────────────
    action_plan = []

    if diagnosis == "MARKET SILENCE (VALID)":
        action_plan = [
            "No action needed — silence is genuine.",
            "Thresholds no longer auto-relax during silence (2026-08-14 policy: tighten "
            "on poor performance, never relax just to manufacture a signal — see "
            "PERFORMANCE_TIGHTENING in calibration_params).",
            "This diagnostic samples 1h only — check other timeframes via "
            "POST /api/v1/bot/analyze-multi-tf before concluding signals are absent; "
            "a quiet 1h doesn't mean 15m/4h are quiet too.",
            "Monitor: if silence continues > 12h on TRENDING symbols across ALL "
            "timeframes → investigate data feed.",
        ]
    elif diagnosis == "SYSTEM OVER-FILTERING":
        if "Cooldown" in diagnosis_reason:
            action_plan = [
                f"ACTION: Reduce cooldown for {_DIAG_TIMEFRAME} from {_engine._COOLDOWN_SEC.get(_DIAG_TIMEFRAME,3600)}s.",
                "Safe range: RANGING→1h, TRENDING→2h (already handled by auto-calibration).",
                "Check: are signals being issued but not tracked in _last_signal_time?",
            ]
        elif "gate" in diagnosis_reason.lower() or "RR" in most_common_rej:
            action_plan = [
                f"Most rejected by: {most_common_rej}",
                "Safe fix: auto-calibration already reduces min_rr based on winrate.",
                f"Current engine winrate: {round(_engine.get_winrate()*100,1)}% — if <40% min_rr=1.6 (strict is correct).",
                "Consider: is sweep detection too strict? Check ICT engine sweep quality thresholds.",
            ]
        else:
            action_plan = [
                f"Most rejected by: {most_common_rej}",
                f"avg_delta={avg_delta} vs required — thresholds no longer auto-relax on "
                "silence or low pass_rate (2026-08-14 policy: tighten, never relax).",
                "Check other timeframes via POST /api/v1/bot/analyze-multi-tf before "
                "concluding signals are absent — this diagnostic samples 1h only.",
                "If genuinely over-filtered across all 3 timeframes for multiple days, "
                "that's a manual product-policy review, not an auto-relax target.",
            ]
    else:
        action_plan = ["Investigate further — run diagnostic again in 30 minutes."]

    results["step8_action_plan"] = {
        "diagnosis": diagnosis,
        "actions":   action_plan,
    }

    elapsed_ms = int((_t.time() - started) * 1000)
    results["diagnostic_meta"] = {
        "elapsed_ms":  elapsed_ms,
        "symbols":     _DIAG_SYMBOLS,
        "timeframe":   _DIAG_TIMEFRAME,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    logger.info(f"🔬 Diagnostic complete in {elapsed_ms}ms — verdict: {diagnosis}")
    return results
