"""
Mosh AI Pro v5 - Admin API
Full control: Users, Payments, Markets
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from loguru import logger

from app.database import get_db
from app.models.user import User, UserRole, PlanType
from app.models.payment import Payment, PaymentStatus, PaymentPlan
from app.models.market_config import MarketConfig
from app.services.auth_service import get_admin_user

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

class MarketIn(BaseModel):
    symbol:       str
    display_name: str
    category:     str = "forex"
    is_active:    bool = True
    is_premium:   bool = False
    yf_symbol:    str = ""
    td_symbol:    str = ""
    sort_order:   int = 0


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
    user.plan                = PlanType.TRIAL
    user.trial_analyses_left = 10
    user.trial_chat_left     = 20
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

    elif data.action == "reject":
        payment.status     = PaymentStatus.REJECTED
        payment.admin_note = data.admin_note
        logger.info(f"❌ Payment rejected: id={payment_id}")
    else:
        raise HTTPException(400, "action يجب أن يكون approve أو reject")

    db.commit()
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
