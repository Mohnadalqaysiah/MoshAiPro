"""
Mosh AI Pro v5 - Auth API
Register / Login / Profile / Link Telegram
"""
from datetime import datetime, timedelta, timezone
import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from loguru import logger

from app.database import get_db
from app.models.user import User, UserRole, PlanType
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


# ─── Register ─────────────────────────────────────────────────────────────────

@router.post("/register")
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email.lower()).first():
        raise HTTPException(400, "البريد الإلكتروني مسجّل مسبقاً")

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
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_token(user.id, user.role)
    logger.info(f"✅ New user registered: {user.email}")
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

    bot_username = getattr(settings, "TELEGRAM_BOT_USERNAME", "MoshAiProBot")
    link = f"https://t.me/{bot_username}?start={user.telegram_link_token}"
    return {
        "token": user.telegram_link_token,
        "link": link,
        "already_linked": bool(user.telegram_id),
        "telegram_username": user.telegram_username,
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
    }
