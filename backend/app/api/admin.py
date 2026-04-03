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
                        logger.info(
                            f"💰 Affiliate commission: referrer_id={ref_aff.user_id} "
                            f"tier={tier} rate={rate*100:.0f}% earned={commission}$"
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
    """إرسال رسالة تيليجرام"""
    url = f"https://api.telegram.org/bot{_settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        return resp.status_code == 200
    except:
        return False

@router.post("/telegram/send")
def send_telegram_message(
    data: TelegramMessageIn,
    background: BackgroundTasks,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """إرسال رسالة تيليجرام للمستخدمين"""
    if not _settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(400, "TELEGRAM_BOT_TOKEN غير مضبوط")

    # بناء الرسالة
    text = ""
    if data.title:
        text += f"<b>{data.title}</b>\n\n"
    text += data.message

    if data.user_ids:
        # إرسال لمستخدمين محددين
        users = db.query(User).filter(User.id.in_(data.user_ids), User.telegram_id != None).all()
        sent = 0
        for u in users:
            if _send_telegram_message(u.telegram_id, text):
                sent += 1
        return {"message": f"تم إرسال {sent} رسالة من {len(users)}", "sent": sent, "total": len(users)}
    else:
        # إرسال لجميع المستخدمين الذين لديهم telegram_id
        users = db.query(User).filter(User.telegram_id != None, User.is_active == True).all()
        sent = 0
        for u in users:
            if background:
                background.add_task(_send_telegram_message, u.telegram_id, text)
                sent += 1
            else:
                if _send_telegram_message(u.telegram_id, text):
                    sent += 1
        return {"message": f"جاري إرسال {sent} رسالة في الخلفية", "sent": sent, "total": len(users)}


# ─── Signal Performance ───────────────────────────────────────────────────────

class SignalOutcomeIn(BaseModel):
    status: str  # "TP1_HIT", "TP2_HIT", "SL_HIT", "EXPIRED"
    closed_price: Optional[float] = None  # optional, auto-derived from TP/SL if not given


def _calc_points(market: str, price_diff: float) -> float:
    """
    Unified pip points — 1 point = 1 pip per market standard
    All metals use ×100  →  $0.01 move = 1 pt (XAUUSD $47 move = 4700 pts)
    Crypto uses ×1       →  $1   move = 1 pt (BTC $500 move = 500 pts)
    Forex/JPY uses ×10000/×100 → standard pips
    """
    symbol = (market or "").upper()
    if symbol in ("XAUUSD", "XAGUSD", "XPTUSD", "XPDUSD"):
        return round(price_diff * 100, 2)    # metals: $0.01 per pip
    elif symbol in ("BTCUSD", "ETHUSD", "BNBUSD"):
        return round(price_diff * 1.0, 2)    # crypto: $1 per pip
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
