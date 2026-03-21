"""
Mosh AI Pro v5 - Auth API
Register / Login / Profile / Link Telegram
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from loguru import logger

from app.database import get_db
from app.models.user import User, UserRole, PlanType
from app.services.auth_service import (
    hash_password, verify_password, create_token,
    get_current_user, check_subscription
)

router = APIRouter()

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
        trial_started_at = now,
        trial_ends_at    = now + timedelta(days=TRIAL_DAYS),
        trial_analyses_left = 10,
        trial_chat_left     = 20,
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
        "telegram_id":         user.telegram_id,
        "created_at":          user.created_at.isoformat() if user.created_at else None,
    }
