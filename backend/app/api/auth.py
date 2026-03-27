"""
Mosh AI Pro v5 - Auth API
Register / Login / Profile / Link Telegram
"""
from datetime import datetime, timedelta, timezone
import secrets
import random
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from loguru import logger

from app.database import get_db
from app.models.user import User, UserRole, PlanType
from app.models.affiliate import Affiliate, generate_affiliate_code
from app.models.site_settings import SiteSettings
from app.services.auth_service import (
    hash_password, verify_password, create_token,
    get_current_user, check_subscription
)
from app.config import get_settings

router = APIRouter()
settings = get_settings()

TRIAL_DAYS = 7


# ─── Schemas ──────────────────────────────────────────────────────────────────

class RegisterIn(BaseModel):
    email: str
    password: str
    full_name: str = ""

class LoginIn(BaseModel):
    email: str
    password: str

class LinkTelegramIn(BaseModel):
    telegram_id: str
    telegram_username: str = ""

class BotVerifyIn(BaseModel):
    token: str
    telegram_id: str
    telegram_username: str = ""
    telegram_name: str = ""

class TradingSettingsIn(BaseModel):
    account_balance: float = 10000.0
    risk_percent: float = 1.5

class NotificationPrefsIn(BaseModel):
    notify_watchlist:      list = []
    notify_timeframe:      str  = "1h"
    notify_min_confidence: int  = 65
    notifications_enabled: bool = True
    language:              str  = "ar"

class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str

class UpdateProfileIn(BaseModel):
    full_name: str = ""
    phone_number: str = ""

class ForgotPasswordIn(BaseModel):
    email: str

class ResetPasswordIn(BaseModel):
    email: str
    otp: str
    new_password: str

class ContactIn(BaseModel):
    name: str
    email: str
    subject: str = ""
    message: str

# OTP store: email → {otp, expires_at}
_otp_store: dict = {}


# ─── Register ─────────────────────────────────────────────────────────────────

@router.post("/register")
def register(
    data: RegisterIn,
    background_tasks: BackgroundTasks,
    ref: str = Query(default=""),
    db: Session = Depends(get_db),
):
    if db.query(User).filter(User.email == data.email.lower()).first():
        raise HTTPException(400, "البريد الإلكتروني مسجّل مسبقاً")

    # Resolve referral code (silently ignore invalid/self-referrals)
    referrer = None
    clean_ref = ref.upper().strip() if ref else ""
    if clean_ref:
        referrer = db.query(User).filter(User.affiliate_code == clean_ref).first()
        if referrer and referrer.email == data.email.lower().strip():
            referrer = None  # prevent self-referral

    # Generate unique affiliate code for new user
    new_code = generate_affiliate_code(db)

    now = datetime.now(timezone.utc)
    user = User(
        email         = data.email.lower().strip(),
        password_hash = hash_password(data.password),
        full_name     = data.full_name,
        role          = UserRole.USER,
        plan          = PlanType.TRIAL,
        is_active     = True,
        trial_started_at    = now,
        trial_ends_at       = now + timedelta(days=TRIAL_DAYS),
        trial_analyses_left = 10,
        trial_chat_left     = 20,
        telegram_link_token = secrets.token_urlsafe(16),
        affiliate_code      = new_code,
        referred_by_code    = clean_ref if referrer else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create affiliate profile
    aff = Affiliate(
        user_id             = user.id,
        code                = new_code,
        referred_by_code    = user.referred_by_code,
        total_referrals     = 0,
        pending_balance_usd = 0.0,
        paid_out_usd        = 0.0,
    )
    db.add(aff)
    db.commit()

    token = create_token(user.id, user.role)
    logger.info(f"✅ New user registered: {user.email} (ref={user.referred_by_code or 'none'})")

    # ── إيميل ترحيب في الخلفية ──────────────────────────────────────────
    smtp_pass = settings.SMTP_PASSWORD
    if smtp_pass:
        from app.services.email_service import send_email, welcome_email_body
        body = welcome_email_body(user.full_name or user.email, trial_days=TRIAL_DAYS, trial_analyses=10)
        background_tasks.add_task(send_email, user.email, "مرحباً بك في Qaffel AI 🎉", body, smtp_pass)

    return {"token": token, "user": _user_info(user)}


# ─── Login ────────────────────────────────────────────────────────────────────

@router.post("/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email.lower()).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "البريد أو كلمة المرور غير صحيحة")
    if user.plan == PlanType.BANNED or not user.is_active:
        raise HTTPException(403, "الحساب معلّق. تواصل مع الدعم.")

    token = create_token(user.id, user.role)
    return {"token": token, "user": _user_info(user)}


# ─── Profile ──────────────────────────────────────────────────────────────────

@router.get("/me")
def get_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    status = check_subscription(user, db)
    info = _user_info(user)
    info["subscription_status"] = status
    return info


# ─── Trading Settings ─────────────────────────────────────────────────────────

@router.put("/trading-settings")
def update_trading_settings(
    data: TradingSettingsIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """تحديث إعدادات التداول: رأس المال ونسبة المخاطرة"""
    if data.account_balance < 100:
        raise HTTPException(400, "رأس المال يجب أن يكون 100$ على الأقل")
    if not (0.1 <= data.risk_percent <= 5.0):
        raise HTTPException(400, "نسبة المخاطرة يجب أن تكون بين 0.1% و5%")

    user.account_balance = data.account_balance
    user.risk_percent    = data.risk_percent
    db.commit()
    return {
        "success": True,
        "account_balance": user.account_balance,
        "risk_percent": user.risk_percent,
    }


# ─── Forgot Password (OTP) ────────────────────────────────────────────────────

@router.post("/forgot-password")
def forgot_password(
    data: ForgotPasswordIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """إرسال OTP لاستعادة كلمة المرور"""
    from app.services.email_service import send_email, otp_email_body
    email = data.email.lower().strip()
    user  = db.query(User).filter(User.email == email).first()

    # لا نكشف إن كان البريد مسجلاً أم لا
    if user:
        otp = str(random.randint(100000, 999999))
        _otp_store[email] = {
            "otp": otp,
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10)
        }
        smtp_pass = settings.SMTP_PASSWORD
        background_tasks.add_task(
            send_email, email,
            "رمز التحقق الخاص بك — Qaffel AI",
            otp_email_body(otp), smtp_pass
        )
        logger.info(f"📧 OTP sent to {email}")

    return {"success": True, "message": "إذا كان البريد مسجلاً ستصلك رسالة خلال دقائق"}


@router.post("/reset-password")
def reset_password(data: ResetPasswordIn, db: Session = Depends(get_db)):
    """التحقق من OTP وتغيير كلمة المرور"""
    email  = data.email.lower().strip()
    stored = _otp_store.get(email)

    if not stored:
        raise HTTPException(400, "لم يُطلب رمز تحقق لهذا البريد")
    if datetime.now(timezone.utc) > stored["expires_at"]:
        _otp_store.pop(email, None)
        raise HTTPException(400, "انتهت صلاحية الرمز. اطلب رمزاً جديداً")
    if stored["otp"] != data.otp.strip():
        raise HTTPException(400, "رمز التحقق غير صحيح")
    if len(data.new_password) < 8:
        raise HTTPException(400, "كلمة المرور يجب أن تكون 8 أحرف على الأقل")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, "المستخدم غير موجود")

    user.password_hash = hash_password(data.new_password)
    db.commit()
    _otp_store.pop(email, None)

    logger.info(f"🔑 Password reset via OTP: {email}")
    return {"success": True, "message": "تم تغيير كلمة المرور بنجاح"}


# ─── Contact Form ──────────────────────────────────────────────────────────────

@router.post("/contact")
def send_contact(data: ContactIn, background_tasks: BackgroundTasks):
    """استقبال رسائل صفحة التواصل وإرسالها للدعم"""
    from app.services.email_service import send_email, contact_email_body
    smtp_pass = settings.SMTP_PASSWORD
    body = contact_email_body(data.name, data.email, data.subject, data.message)
    background_tasks.add_task(
        send_email,
        settings.SUPPORT_EMAIL,
        f"[تواصل] {data.subject or 'رسالة جديدة'} — {data.name}",
        body, smtp_pass
    )
    return {"success": True, "message": "تم إرسال رسالتك بنجاح"}


# ─── Change Password ──────────────────────────────────────────────────────────

@router.put("/change-password")
def change_password(
    data: ChangePasswordIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_password(data.old_password, user.password_hash):
        raise HTTPException(400, "كلمة المرور الحالية غير صحيحة")
    if len(data.new_password) < 8:
        raise HTTPException(400, "كلمة المرور الجديدة يجب أن تكون 8 أحرف على الأقل")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    return {"success": True, "message": "تم تغيير كلمة المرور بنجاح"}


# ─── Update Profile ───────────────────────────────────────────────────────────

@router.put("/profile")
def update_profile(
    data: UpdateProfileIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if data.full_name:
        user.full_name = data.full_name.strip()
    if data.phone_number is not None:
        user.phone_number = data.phone_number.strip() or None
    db.commit()
    return {"success": True, "user": _user_info(user)}


# ─── Link Telegram ────────────────────────────────────────────────────────────

@router.post("/link-telegram")
def link_telegram(
    data: LinkTelegramIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if telegram_id already used
    existing = db.query(User).filter(
        User.telegram_id == data.telegram_id,
        User.id != user.id
    ).first()
    if existing:
        raise HTTPException(400, "هذا الحساب Telegram مرتبط بمستخدم آخر")

    user.telegram_id = data.telegram_id
    user.telegram_username = data.telegram_username
    db.commit()
    return {"success": True, "message": "تم ربط حساب Telegram بنجاح"}


# ─── Telegram Link Token ──────────────────────────────────────────────────────

def _get_bot_username(db: Session) -> str:
    """يجلب اسم البوت من قاعدة البيانات أولاً، ثم من الإعدادات"""
    row = db.query(SiteSettings).filter(SiteSettings.key == "telegram_bot_username").first()
    if row and row.value:
        return row.value.strip()
    return getattr(settings, "TELEGRAM_BOT_USERNAME", "Qaffelbot")


@router.get("/telegram-link")
def get_telegram_link(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """يرجع رابط تفعيل البوت الخاص بالمستخدم"""
    if not user.telegram_link_token:
        user.telegram_link_token = secrets.token_urlsafe(16)
        db.commit()
        db.refresh(user)

    bot_username = _get_bot_username(db)
    link = f"https://t.me/{bot_username}?start={user.telegram_link_token}"
    return {
        "token": user.telegram_link_token,
        "link": link,
        "already_linked": bool(user.telegram_id),
        "telegram_username": user.telegram_username,
        "bot_username": bot_username,
    }


@router.post("/relink-telegram")
def relink_telegram(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """يفك ربط Telegram الحالي ويولّد رابط تفعيل جديد"""
    user.telegram_id = None
    user.telegram_username = None
    user.telegram_link_token = secrets.token_urlsafe(16)
    db.commit()
    db.refresh(user)

    bot_username = _get_bot_username(db)
    link = f"https://t.me/{bot_username}?start={user.telegram_link_token}"
    logger.info(f"🔄 Telegram re-link requested: {user.email}")
    return {
        "success": True,
        "token": user.telegram_link_token,
        "link": link,
        "bot_username": bot_username,
    }


@router.post("/bot-verify")
def bot_verify_link(data: BotVerifyIn, db: Session = Depends(get_db)):
    """
    يُستدعى من البوت عند تفعيل /start TOKEN
    يربط telegram_id بالمستخدم
    """
    user = db.query(User).filter(User.telegram_link_token == data.token).first()
    if not user:
        raise HTTPException(400, "رابط التفعيل غير صالح أو منتهي الصلاحية")

    # check if telegram_id used by another
    existing = db.query(User).filter(
        User.telegram_id == data.telegram_id,
        User.id != user.id
    ).first()
    if existing:
        raise HTTPException(400, "هذا الحساب Telegram مرتبط بمستخدم آخر")

    user.telegram_id       = data.telegram_id
    user.telegram_username = data.telegram_username
    user.telegram_link_token = None  # invalidate after use
    db.commit()

    logger.info(f"✅ Telegram linked: {user.email} ↔ @{data.telegram_username}")
    return {
        "success": True,
        "user_name": user.full_name or user.email,
        "plan": user.plan,
        "trial_analyses_left": user.trial_analyses_left,
        "trial_chat_left": user.trial_chat_left,
    }


# ─── Helper ───────────────────────────────────────────────────────────────────

def _user_info(user: User) -> dict:
    now = datetime.now(timezone.utc)
    sub_ends = user.subscription_ends_at
    trial_ends = user.trial_ends_at

    days_left = None
    if user.plan in [PlanType.WEEKLY, PlanType.MONTHLY] and sub_ends:
        delta = sub_ends - now
        days_left = max(0, delta.days)
    elif user.plan == PlanType.TRIAL and trial_ends:
        delta = trial_ends - now
        days_left = max(0, delta.days)

    return {
        "id":          user.id,
        "email":       user.email,
        "full_name":   user.full_name or "",
        "role":        user.role,
        "plan":        user.plan,
        "is_active":   user.is_active,
        "days_left":   days_left,
        "trial_analyses_left": user.trial_analyses_left,
        "trial_chat_left":     user.trial_chat_left,
        "analyses_total":      user.analyses_total,
        "chat_total":          user.chat_total,
        "telegram_id":           user.telegram_id,
        "telegram_username":     user.telegram_username,
        "telegram_linked":       bool(user.telegram_id),
        "created_at":            user.created_at.isoformat() if user.created_at else None,
        "account_balance":       float(user.account_balance or 10000.0),
        "risk_percent":          float(user.risk_percent or 1.5),
        "phone_number":          user.phone_number or "",
        "language":              user.language or "ar",
        "notify_watchlist":      user.notify_watchlist or [],
        "notify_timeframe":      user.notify_timeframe or "1h",
        "notify_min_confidence": user.notify_min_confidence or 65,
        "notifications_enabled": bool(user.notifications_enabled),
        "affiliate_code":        user.affiliate_code or "",
        "referred_by_code":      user.referred_by_code or "",
    }


# ─── Notification Preferences ──────────────────────────────────────────────────

@router.get("/preferences")
def get_preferences(user: User = Depends(get_current_user)):
    return {
        "notify_watchlist":      user.notify_watchlist or [],
        "notify_timeframe":      user.notify_timeframe or "1h",
        "notify_min_confidence": user.notify_min_confidence or 65,
        "notifications_enabled": bool(user.notifications_enabled),
        "language":              user.language or "ar",
        "account_balance":       float(user.account_balance or 10000.0),
        "risk_percent":          float(user.risk_percent or 1.5),
    }


@router.put("/preferences")
def update_preferences(
    data: NotificationPrefsIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user.notify_watchlist      = data.notify_watchlist
    user.notify_timeframe      = data.notify_timeframe
    user.notify_min_confidence = data.notify_min_confidence
    user.notifications_enabled = data.notifications_enabled
    user.language              = data.language
    db.commit()
    return {"success": True}
