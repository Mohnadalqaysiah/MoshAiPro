"""
Mosh AI Pro v5 - Subscription API
Plans, Binance USDT Payment, Status
"""
import copy, json
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from loguru import logger
import stripe

from app.database import get_db
from app.models.user import User, PlanType
from app.models.payment import Payment, PaymentStatus, PaymentPlan
from app.models.site_settings import SiteSettings
from app.services.auth_service import get_current_user, check_subscription
from app.services.subscription_service import activate_subscription_payment
from app.config import get_settings

router  = APIRouter()
settings = get_settings()

# ─── Pricing Config ───────────────────────────────────────────────────────────

PLANS = {
    "weekly": {
        "name":        "الأسبوعية",
        "name_en":     "Weekly",
        "price_usd":   7,
        "days":        7,
        "features":    ["تحليل ICT/SMC كامل", "شات AI غير محدود", "تنبيهات Telegram", "جميع الأزواج", "تحليل متعدد الفريمات"],
        "features_en": ["Full ICT/SMC Analysis", "Unlimited AI Chat", "Telegram Alerts", "All Pairs", "Multi-Timeframe Analysis"],
    },
    "monthly": {
        "name":        "الشهرية",
        "name_en":     "Monthly",
        "price_usd":   30,
        "days":        30,
        "features":    ["كل مزايا الأسبوعي", "أولوية الدعم الفني", "تقارير أسبوعية مفصّلة", "وصول مبكر للمزايا الجديدة", "توفير 46%"],
        "features_en": ["All Weekly Features", "Priority Support", "Detailed Weekly Reports", "Early Access to New Features", "Save 46%"],
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


class StripeCheckoutIn(BaseModel):
    plan: str    # weekly | monthly


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _resolve_plans(db: Session) -> dict:
    """Builds the PLANS dict with SiteSettings overrides applied."""
    db_settings = {r.key: r.value for r in db.query(SiteSettings).all()}

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
        # Days override
        days_val = db_settings.get(f"plan_{plan_key}_days")
        if days_val:
            try:
                plans[plan_key]["days"] = int(days_val)
            except Exception:
                pass

    return plans


def _setting(db: Session, key: str, fallback: str) -> str:
    """DB override first (SiteSettings), then env/config fallback — same pattern as telegram_bot_token."""
    row = db.query(SiteSettings).filter(SiteSettings.key == key).first()
    if row and row.value and row.value.strip():
        return row.value.strip()
    return fallback


def _stripe_config(db: Session) -> dict:
    enabled_val = _setting(db, "stripe_enabled", "true")
    return {
        "enabled":          enabled_val.strip().lower() != "false",
        "secret_key":       _setting(db, "stripe_secret_key", settings.STRIPE_SECRET_KEY),
        "publishable_key":  _setting(db, "stripe_publishable_key", ""),
        "webhook_secret":   _setting(db, "stripe_webhook_secret", settings.STRIPE_WEBHOOK_SECRET),
        "success_url":      _setting(db, "stripe_success_url", settings.STRIPE_SUCCESS_URL),
        "cancel_url":       _setting(db, "stripe_cancel_url", settings.STRIPE_CANCEL_URL),
    }


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/plans")
def get_plans(db: Session = Depends(get_db)):
    db_settings = {r.key: r.value for r in db.query(SiteSettings).all()}
    wallet = db_settings.get("usdt_wallet") or USDT_WALLET
    plans  = _resolve_plans(db)
    stripe_cfg = _stripe_config(db)

    return {
        "plans": plans,
        "wallet": wallet,
        "network": USDT_NETWORK,
        "note": "أرسل المبلغ بالضبط بالـ USDT ثم أدخل رقم المعاملة (TxID) للتحقق",
        "card_payment_enabled": stripe_cfg["enabled"] and bool(stripe_cfg["secret_key"]),
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
    background_tasks: BackgroundTasks,
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

    # ── تنبيه الأدمن عبر Telegram ────────────────────────────────────────
    from app.services.admin_notify import notify_admin_telegram
    _plan_name = {"weekly": "أسبوعية ($7)", "monthly": "شهرية ($30)"}.get(data.plan, data.plan)
    _msg = (
        f"💳 <b>طلب دفع جديد!</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📧 المستخدم: <code>{user.email}</code>\n"
        f"📦 الباقة: {_plan_name}\n"
        f"💰 المبلغ: ${plan_info['price_usd']} USDT\n"
        f"🌐 الشبكة: {data.network}\n"
        f"🔑 TxID: <code>{data.tx_id}</code>\n"
        f"🆔 Payment ID: {payment.id}"
    )
    background_tasks.add_task(notify_admin_telegram, _msg)

    return {
        "success": True,
        "message": "تم استلام طلب الدفع. سيتم التفعيل خلال 30 دقيقة بعد التحقق.",
        "payment_id": payment.id,
    }


@router.post("/stripe/checkout")
def create_stripe_checkout(
    data: StripeCheckoutIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if data.plan not in PLANS:
        raise HTTPException(400, "باقة غير صحيحة")

    cfg = _stripe_config(db)
    if not cfg["enabled"] or not cfg["secret_key"]:
        raise HTTPException(500, "الدفع بالبطاقة غير متاح حالياً")

    plan_info = _resolve_plans(db)[data.plan]

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": f"Qaffel AI — {plan_info['name_en']} Plan"},
                    "unit_amount": int(round(plan_info["price_usd"] * 100)),
                },
                "quantity": 1,
            }],
            success_url=cfg["success_url"],
            cancel_url=cfg["cancel_url"],
            client_reference_id=str(user.id),
            customer_email=user.email,
            metadata={"user_id": str(user.id), "plan": data.plan},
            api_key=cfg["secret_key"],
        )
    except Exception as e:
        logger.error(f"❌ Stripe checkout session error: {e}")
        raise HTTPException(500, "تعذّر إنشاء جلسة الدفع، حاول لاحقاً")

    return {"url": session.url}


@router.post("/stripe/payment-intent")
def create_stripe_payment_intent(
    data: StripeCheckoutIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """إنشاء PaymentIntent لعرض نموذج بطاقة مدمج داخل الصفحة (Stripe Elements)
    بدون تحويل المستخدم لصفحة Stripe المستضافة."""
    if data.plan not in PLANS:
        raise HTTPException(400, "باقة غير صحيحة")

    cfg = _stripe_config(db)
    if not cfg["enabled"] or not cfg["secret_key"]:
        raise HTTPException(500, "الدفع بالبطاقة غير متاح حالياً")

    plan_info = _resolve_plans(db)[data.plan]

    try:
        intent = stripe.PaymentIntent.create(
            amount=int(round(plan_info["price_usd"] * 100)),
            currency="usd",
            automatic_payment_methods={"enabled": True},
            receipt_email=user.email,
            description=f"Qaffel AI — {plan_info['name_en']} Plan",
            metadata={"user_id": str(user.id), "plan": data.plan},
            api_key=cfg["secret_key"],
        )
    except Exception as e:
        logger.error(f"❌ Stripe payment intent error: {e}")
        raise HTTPException(500, "تعذّر بدء عملية الدفع، حاول لاحقاً")

    return {
        "client_secret": intent.client_secret,
        "publishable_key": cfg["publishable_key"],
    }


@router.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    payload    = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    cfg        = _stripe_config(db)

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, cfg["webhook_secret"])
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        logger.warning(f"⚠️ Stripe webhook signature verification failed: {e}")
        raise HTTPException(400, "Invalid signature")

    if event["type"] == "checkout.session.completed":
        session  = event["data"]["object"]
        metadata = session.get("metadata") or {}
        _finalize_stripe_payment(
            db, background_tasks,
            user_id=metadata.get("user_id"), plan_key=metadata.get("plan"),
            tx_id=session["id"], payment_intent_id=session.get("payment_intent"),
        )

    elif event["type"] == "payment_intent.succeeded":
        # نموذج البطاقة المدمج بالصفحة (Stripe Elements) — بدون تحويل خارجي
        intent   = event["data"]["object"]
        metadata = intent.get("metadata") or {}
        _finalize_stripe_payment(
            db, background_tasks,
            user_id=metadata.get("user_id"), plan_key=metadata.get("plan"),
            tx_id=intent["id"], payment_intent_id=intent["id"],
        )

    return {"received": True}


def _finalize_stripe_payment(
    db: Session, background_tasks: BackgroundTasks,
    user_id: Optional[str], plan_key: Optional[str],
    tx_id: str, payment_intent_id: Optional[str],
) -> None:
    """Shared activation logic for both the hosted-Checkout and embedded
    PaymentIntent flows — idempotent on `tx_id` since Stripe may retry events."""
    if not user_id or plan_key not in PLANS:
        logger.warning(f"⚠️ Stripe webhook missing/invalid metadata: user_id={user_id} plan={plan_key}")
        return

    if db.query(Payment).filter(Payment.tx_id == tx_id).first():
        return

    plan_info = _resolve_plans(db)[plan_key]

    payment = Payment(
        user_id     = int(user_id),
        plan        = PaymentPlan(plan_key),
        amount_usd  = plan_info["price_usd"],
        network     = "stripe",
        provider    = "stripe",
        tx_id       = tx_id,
        stripe_payment_intent = payment_intent_id,
        status      = PaymentStatus.APPROVED,
    )
    db.add(payment)
    db.flush()

    user = activate_subscription_payment(db, payment, background_tasks)
    db.commit()

    if user:
        logger.info(f"💳 Stripe payment completed: user={user.email} plan={plan_key} tx={tx_id}")
        from app.services.admin_notify import notify_admin_telegram
        _plan_name = {"weekly": "أسبوعية", "monthly": "شهرية"}.get(plan_key, plan_key)
        _msg = (
            f"💳 <b>دفعة Stripe جديدة (مفعّلة تلقائياً)!</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📧 المستخدم: <code>{user.email}</code>\n"
            f"📦 الباقة: {_plan_name}\n"
            f"💰 المبلغ: ${plan_info['price_usd']}\n"
            f"🆔 Payment ID: {payment.id}"
        )
        background_tasks.add_task(notify_admin_telegram, _msg)


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
        "provider":   p.provider,
        "tx_id":      p.tx_id,
        "status":     p.status,
        "admin_note": p.admin_note,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }
