"""
Mosh AI Pro v5 - Subscription API
Plans, Binance USDT Payment, Status
"""
import copy, json
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from loguru import logger

from app.database import get_db
from app.models.user import User, PlanType
from app.models.payment import Payment, PaymentStatus, PaymentPlan
from app.models.site_settings import SiteSettings
from app.services.auth_service import get_current_user, check_subscription
from app.config import get_settings

router  = APIRouter()
settings = get_settings()

# ─── Pricing Config ───────────────────────────────────────────────────────────

PLANS = {
    "weekly": {
        "name":        "الباقة الأسبوعية",
        "price_usd":   7,
        "days":        7,
        "analyses":    "غير محدود",
        "chat":        "غير محدود",
        "features":    ["تحليل ICT/SMC كامل", "وكيل الدردشة الذكي", "تنبيهات Telegram", "جميع الأزواج"],
    },
    "monthly": {
        "name":        "الباقة الشهرية",
        "price_usd":   30,
        "days":        30,
        "analyses":    "غير محدود",
        "chat":        "غير محدود",
        "features":    ["كل مزايا الأسبوعية", "أولوية الدعم", "تقارير مفصّلة", "توفير 46%"],
        "popular":     True,
    },
}

USDT_WALLET = getattr(settings, "USDT_WALLET_ADDRESS", "TQoS5Z...")  # يُعيَّن في .env
USDT_NETWORK = getattr(settings, "USDT_NETWORK", "TRC20")


# ─── Schemas ──────────────────────────────────────────────────────────────────

class PaymentIn(BaseModel):
    plan:    str    # weekly | monthly
    tx_id:   str    # Binance TxID
    network: str = "TRC20"


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/plans")
def get_plans(db: Session = Depends(get_db)):
    # Read all settings at once
    db_settings = {r.key: r.value for r in db.query(SiteSettings).all()}

    wallet = db_settings.get("usdt_wallet") or USDT_WALLET

    # Build plans with DB overrides
    plans = copy.deepcopy(PLANS)
    for plan_key in ("weekly", "monthly"):
        # Price override
        price_val = db_settings.get(f"plan_{plan_key}_price")
        if price_val:
            try:
                plans[plan_key]["price_usd"] = float(price_val)
            except Exception:
                pass
        # Name override (Arabic)
        name_val = db_settings.get(f"plan_{plan_key}_name")
        if name_val:
            plans[plan_key]["name"] = name_val
        # English name
        name_en_val = db_settings.get(f"plan_{plan_key}_name_en")
        if name_en_val:
            plans[plan_key]["name_en"] = name_en_val
        # Features override (JSON array)
        feat_val = db_settings.get(f"plan_{plan_key}_features")
        if feat_val:
            try:
                plans[plan_key]["features"] = json.loads(feat_val)
            except Exception:
                pass
        # English features
        feat_en_val = db_settings.get(f"plan_{plan_key}_features_en")
        if feat_en_val:
            try:
                plans[plan_key]["features_en"] = json.loads(feat_en_val)
            except Exception:
                pass

    return {
        "plans": plans,
        "wallet": wallet,
        "network": USDT_NETWORK,
        "note": "أرسل المبلغ بالضبط بالـ USDT ثم أدخل رقم المعاملة (TxID) للتحقق"
    }


@router.get("/status")
def get_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    status = check_subscription(user, db)
    payments = db.query(Payment).filter(
        Payment.user_id == user.id
    ).order_by(Payment.created_at.desc()).limit(5).all()

    return {
        "plan":   user.plan,
        "status": status,
        "payments": [_payment_info(p) for p in payments],
    }


@router.post("/pay")
def submit_payment(
    data: PaymentIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if data.plan not in PLANS:
        raise HTTPException(400, "باقة غير صحيحة")

    # هل TxID مستخدم؟
    if db.query(Payment).filter(Payment.tx_id == data.tx_id).first():
        raise HTTPException(400, "رقم المعاملة مستخدم مسبقاً")

    plan_info = PLANS[data.plan]
    payment = Payment(
        user_id    = user.id,
        plan       = PaymentPlan(data.plan),
        amount_usd = plan_info["price_usd"],
        network    = data.network,
        tx_id      = data.tx_id.strip(),
        status     = PaymentStatus.PENDING,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    logger.info(f"💳 Payment submitted: user={user.email} plan={data.plan} tx={data.tx_id}")
    return {
        "success": True,
        "message": "تم استلام طلب الدفع. سيتم التفعيل خلال 30 دقيقة بعد التحقق.",
        "payment_id": payment.id,
    }


@router.get("/payments")
def my_payments(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    payments = db.query(Payment).filter(
        Payment.user_id == user.id
    ).order_by(Payment.created_at.desc()).all()
    return [_payment_info(p) for p in payments]


# ─── Helper ───────────────────────────────────────────────────────────────────

def _payment_info(p: Payment) -> dict:
    return {
        "id":         p.id,
        "plan":       p.plan,
        "amount_usd": p.amount_usd,
        "network":    p.network,
        "tx_id":      p.tx_id,
        "status":     p.status,
        "admin_note": p.admin_note,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }
