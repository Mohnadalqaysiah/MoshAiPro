"""
Mosh AI Pro v5 - Auth Service
JWT Authentication + Password Hashing
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger

from app.database import get_db
from app.models.user import User, PlanType
from app.config import get_settings

settings = get_settings()
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer  = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"


# ─── Password ─────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)


# ─── JWT ──────────────────────────────────────────────────────────────────────

def create_token(user_id: int, role: str, expires_days: int = 30) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=expires_days)
    payload = {"sub": str(user_id), "role": role, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# ─── Dependencies ─────────────────────────────────────────────────────────────

def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    db: Session = Depends(get_db)
) -> User:
    if not creds:
        raise HTTPException(status_code=401, detail="يجب تسجيل الدخول أولاً")

    payload = decode_token(creds.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="جلسة منتهية أو غير صالحة")

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="المستخدم غير موجود")
    if not user.is_active or user.plan == PlanType.BANNED:
        raise HTTPException(status_code=403, detail="الحساب معلّق. تواصل مع الدعم.")

    # تحديث آخر نشاط
    user.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    return user


def get_admin_user(user: User = Depends(get_current_user)) -> User:
    from app.models.user import UserRole
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="صلاحيات المسؤول مطلوبة")
    return user


# ─── Subscription Check ────────────────────────────────────────────────────────

def check_subscription(user: User, db: Session) -> dict:
    """
    يفحص صلاحية الاشتراك ويرجع الحالة
    """
    from app.models.user import PlanType
    now = datetime.now(timezone.utc)

    # مسؤول = كل شيء مسموح
    from app.models.user import UserRole
    if user.role == UserRole.ADMIN:
        return {"allowed": True, "plan": "admin", "reason": ""}

    # محظور
    if user.plan == PlanType.BANNED or not user.is_active:
        return {"allowed": False, "plan": "banned", "reason": "الحساب محظور"}

    # اشتراك أسبوعي أو شهري نشط
    if user.plan in [PlanType.WEEKLY, PlanType.MONTHLY]:
        if user.subscription_ends_at and user.subscription_ends_at > now:
            return {"allowed": True, "plan": user.plan, "reason": ""}
        else:
            # انتهى الاشتراك → تجريبي
            user.plan = PlanType.TRIAL
            db.commit()

    # تجريبي
    if user.plan == PlanType.TRIAL:
        if user.trial_ends_at and user.trial_ends_at < now:
            return {
                "allowed": False,
                "plan": "trial_expired",
                "reason": "انتهت الفترة التجريبية. اشترك للمتابعة.",
                "upgrade": True,
            }
        return {
            "allowed": True,
            "plan": "trial",
            "reason": "",
            "analyses_left": user.trial_analyses_left,
            "chat_left": user.trial_chat_left,
        }

    return {"allowed": False, "plan": "unknown", "reason": "حالة غير معروفة"}


def deduct_trial(user: User, db: Session, kind: str = "analysis"):
    """خصم كريدت من التجربة"""
    if kind == "analysis":
        user.trial_analyses_left = max(0, user.trial_analyses_left - 1)
        user.analyses_total += 1
        user.analyses_used_today += 1
    else:
        user.trial_chat_left = max(0, user.trial_chat_left - 1)
        user.chat_total += 1
        user.chat_used_today += 1
    db.commit()
