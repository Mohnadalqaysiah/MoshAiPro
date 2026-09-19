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
import requests
import stripe

from app.database import get_db
from app.models.user import User, PlanType
from app.models.payment import Payment, PaymentStatus, PaymentPlan
from app.models.site_settings import SiteSettings
from app.services.auth_service import get_current_user, check_subscription
from app.services.subscription_service import activate_subscription_payment
from app.services.coupon_service import find_coupon
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
    "yearly": {
        "name":        "السنوية",
        "name_en":     "Yearly",
        "price_usd":   179.9,
        "days":        365,
        "features":    ["كل مزايا الشهري", "أفضل قيمة — شهران مجاناً", "سعر مثبَّت طوال السنة", "أولوية الدعم الفني", "وصول مبكر للمزايا الجديدة"],
        "features_en": ["All Monthly Features", "Best value — two months free", "Price locked for the year", "Priority Support", "Early Access to New Features"],
        "best_value":  True,
    },
}

# مفاتيح الباقات بترتيب العرض — مصدر واحد بدل تكرار الصفوف بكل حلقة
PLAN_KEYS = tuple(PLANS.keys())

USDT_WALLET = getattr(settings, "USDT_WALLET_ADDRESS", "TQoS5Z...")  # يُعيَّن في .env
USDT_NETWORK = getattr(settings, "USDT_NETWORK", "TRC20")


# ─── Schemas ──────────────────────────────────────────────────────────────────

class PaymentIn(BaseModel):
    plan:    str    # weekly | monthly | yearly
    tx_id:   str    # Binance TxID
    network: str = "TRC20"
    coupon_code: Optional[str] = None


class StripeCheckoutIn(BaseModel):
    plan: str    # weekly | monthly | yearly
    coupon_code: Optional[str] = None


class SpaceremitVerifyIn(BaseModel):
    plan:            str    # weekly | monthly | yearly
    spaceremit_code: str    # SP_payment_code returned by the client-side widget
    coupon_code:     Optional[str] = None


class PayPalOrderIn(BaseModel):
    plan: str    # weekly | monthly | yearly
    coupon_code: Optional[str] = None


class PayPalCaptureIn(BaseModel):
    order_id: str


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _resolve_plans(db: Session) -> dict:
    """Builds the PLANS dict with SiteSettings overrides applied."""
    db_settings = {r.key: r.value for r in db.query(SiteSettings).all()}

    plans = copy.deepcopy(PLANS)
    for plan_key in PLAN_KEYS:
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


def _priced(db: Session, plan_key: str, coupon_code: Optional[str],
            user_id: Optional[int]) -> tuple[dict, float, object]:
    """
    (معلومات الباقة، السعر النهائي، الكوبون) — نقطة التسعير الوحيدة لكل
    مسارات الدفع. رمز غير صالح يرفع 400 بدل تمريره بالسعر الكامل: المستخدم
    أدخل رمزاً ويتوقّع خصمه، فالخصم الصامت الفاشل بيعٌ بسعر لم يوافق عليه.
    """
    from app.services.coupon_service import price_for
    plans = _resolve_plans(db)
    if plan_key not in plans:
        raise HTTPException(400, "باقة غير صحيحة")
    plan_info = plans[plan_key]
    final, coupon, err = price_for(db, plan_info, plan_key, coupon_code, user_id)
    if err:
        raise HTTPException(400, err)
    return plan_info, final, coupon


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


def _paypal_config(db: Session) -> dict:
    """
    "الدفع بالبطاقة" بالواجهة — بلا أي اسم معالج ظاهر للعميل. يُعالَج
    بالخلفية عبر PayPal Advanced Card Payments (حقول بطاقة مستضافة بلا
    شعار PayPal)، بنفس منطق DB-أولاً-ثم-env المتّبع بـStripe/Spaceremit.
    المفاتيح تُدار من لوحة الإدارة عادةً — راجع Admin.jsx قسم PayPal.
    """
    test_mode = _setting(db, "paypal_test_mode", "false").strip().lower() == "true"
    prefix = "paypal_test_" if test_mode else "paypal_"
    env_client = settings.PAYPAL_TEST_CLIENT_ID if test_mode else settings.PAYPAL_CLIENT_ID
    env_secret = settings.PAYPAL_TEST_SECRET_KEY if test_mode else settings.PAYPAL_SECRET_KEY
    env_webhook = settings.PAYPAL_TEST_WEBHOOK_ID if test_mode else settings.PAYPAL_WEBHOOK_ID
    return {
        "enabled":    _setting(db, "paypal_enabled", "false").strip().lower() == "true",
        "test_mode":  test_mode,
        "client_id":  _setting(db, f"{prefix}client_id", env_client),
        "secret_key": _setting(db, f"{prefix}secret_key", env_secret),
        "webhook_id": _setting(db, f"{prefix}webhook_id", env_webhook),
        "base_url":   "https://api-m.sandbox.paypal.com" if test_mode else "https://api-m.paypal.com",
    }


# كاش توكن OAuth بالذاكرة — صالح عادة ~9 ساعات (PayPal ترجعه بـexpires_in)،
# فطلبه بكل استدعاء تحميل شبكة بلا داعٍ. لا يحتاج قفل: نفس القيمة تُكتب
# بأسوأ الأحوال مرتين بتزامن نادر، بلا ضرر.
_paypal_token_cache: dict = {}


def _paypal_access_token(cfg: dict) -> str:
    cache_key = (cfg["client_id"], cfg["base_url"])
    now = datetime.now(timezone.utc).timestamp()
    cached = _paypal_token_cache.get(cache_key)
    if cached and cached["expires_at"] > now + 60:
        return cached["token"]

    resp = requests.post(
        f"{cfg['base_url']}/v1/oauth2/token",
        auth=(cfg["client_id"], cfg["secret_key"]),
        data={"grant_type": "client_credentials"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    _paypal_token_cache[cache_key] = {
        "token": data["access_token"],
        "expires_at": now + int(data.get("expires_in", 3000)),
    }
    return data["access_token"]


def _paypal_custom_id(user_id: int, plan_key: str, coupon_code: Optional[str]) -> str:
    return f"u{user_id}|{plan_key}|{coupon_code or ''}"


def _parse_paypal_custom_id(custom_id: str):
    """يعيد (user_id, plan_key, coupon_code) أو (None, None, None) لو الصيغة غير متوقَّعة."""
    try:
        owner_raw, plan_key, cp_code = (custom_id.split("|") + ["", ""])[:3]
        return int(owner_raw.lstrip("u")), plan_key, (cp_code or None)
    except Exception:
        return None, None, None


def _finalize_paypal_payment(
    db: Session, background_tasks: BackgroundTasks,
    user_id: int, plan_key: str, capture_id: str, charged: float,
    coupon_code: Optional[str] = None,
) -> Payment:
    """idempotent على capture_id — نفس مبدأ Stripe/Spaceremit: إعادة محاولة
    الفرونت بعد انقطاع شبكة، أو وصول الويبهوك بعد /capture-order، لا يجب
    أن يُفعِّل الاشتراك مرتين."""
    existing = db.query(Payment).filter(Payment.tx_id == capture_id).first()
    if existing:
        return existing

    plan_info = _resolve_plans(db)[plan_key]
    _coupon = find_coupon(db, coupon_code) if coupon_code else None

    payment = Payment(
        user_id     = user_id,
        plan        = PaymentPlan(plan_key),
        amount_usd  = charged,
        coupon_code      = _coupon.code if _coupon else None,
        discount_percent = _coupon.discount_percent if _coupon else None,
        network     = "paypal",
        provider    = "paypal",
        tx_id       = capture_id,
        status      = PaymentStatus.APPROVED,
    )
    db.add(payment)
    db.flush()

    user = activate_subscription_payment(db, payment, background_tasks)
    db.commit()

    if user:
        logger.info(f"💳 PayPal payment completed: user={user.email} plan={plan_key} tx={capture_id}")
        from app.services.admin_notify import notify_admin_telegram
        _plan_name = plan_info.get("name") or plan_key
        _msg = (
            f"💳 <b>دفعة بطاقة جديدة (مفعّلة تلقائياً)!</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📧 المستخدم: <code>{user.email}</code>\n"
            f"📦 الباقة: {_plan_name}\n"
            f"💰 المبلغ: ${charged:g}"
            + (f" (كوبون {_coupon.code} −{_coupon.discount_percent:g}%)" if _coupon else "")
            + "\n"
            f"🆔 Payment ID: {payment.id}"
        )
        background_tasks.add_task(notify_admin_telegram, _msg)

    return payment


SPACEREMIT_API_URL      = "https://spaceremit.com/api/v2/payment_info/"
SPACEREMIT_ACCEPTED_TAGS = {"A", "B", "D", "E"}  # Completed / Pending / Holding / Needs Review — funds committed


def _spaceremit_config(db: Session) -> dict:
    test_mode = _setting(db, "spaceremit_test_mode", "false").strip().lower() == "true"
    return {
        "enabled":    _setting(db, "spaceremit_enabled", "false").strip().lower() == "true",
        "test_mode":  test_mode,
        "public_key": _setting(
            db, "spaceremit_test_public_key" if test_mode else "spaceremit_public_key",
            settings.SPACEREMIT_TEST_PUBLIC_KEY if test_mode else settings.SPACEREMIT_PUBLIC_KEY,
        ),
        "secret_key": _setting(
            db, "spaceremit_test_secret_key" if test_mode else "spaceremit_secret_key",
            settings.SPACEREMIT_TEST_SECRET_KEY if test_mode else settings.SPACEREMIT_SECRET_KEY,
        ),
    }


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/plans")
def get_plans(db: Session = Depends(get_db)):
    db_settings = {r.key: r.value for r in db.query(SiteSettings).all()}
    wallet = db_settings.get("usdt_wallet") or USDT_WALLET
    plans  = _resolve_plans(db)
    paypal_cfg = _paypal_config(db)
    paypal_ready = paypal_cfg["enabled"] and bool(paypal_cfg["client_id"]) and bool(paypal_cfg["secret_key"])
    spaceremit_cfg = _spaceremit_config(db)
    spaceremit_ready = spaceremit_cfg["enabled"] and bool(spaceremit_cfg["secret_key"]) and bool(spaceremit_cfg["public_key"])

    return {
        "plans": plans,
        "wallet": wallet,
        "network": USDT_NETWORK,
        "note": "أرسل المبلغ بالضبط بالـ USDT ثم أدخل رقم المعاملة (TxID) للتحقق",
        # (2026-09-19) "الدفع بالبطاقة" بالواجهة عام بلا اسم معالج — كان
        # مصدره Stripe، صار PayPal Advanced Card Payments (حقول بطاقة بلا
        # شعار). Stripe يبقى بالكود بلا حذف (dormant) لو احتجناه لاحقاً.
        "card_payment_enabled": paypal_ready,
        "spaceremit_enabled": spaceremit_ready,
        "spaceremit_public_key": spaceremit_cfg["public_key"] if spaceremit_ready else "",
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
    # هل TxID مستخدم؟
    if db.query(Payment).filter(Payment.tx_id == data.tx_id).first():
        raise HTTPException(400, "رقم المعاملة مستخدم مسبقاً")

    # (2026-09-16) كان PLANS[...] الثابت هنا بينما بقية المسارات تستخدم
    # _resolve_plans — أي أن تعديل السعر من لوحة الإدارة كان يسري على
    # الدفع بالبطاقة ولا يسري على USDT. وُحِّد عبر _priced.
    plan_info, final_price, coupon = _priced(db, data.plan, data.coupon_code, user.id)

    payment = Payment(
        user_id    = user.id,
        plan       = PaymentPlan(data.plan),
        amount_usd = final_price,
        network    = data.network,
        tx_id      = data.tx_id.strip(),
        status     = PaymentStatus.PENDING,
        coupon_code      = coupon.code if coupon else None,
        discount_percent = coupon.discount_percent if coupon else None,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    logger.info(f"💳 Payment submitted: user={user.email} plan={data.plan} tx={data.tx_id}")

    # ── تنبيه الأدمن عبر Telegram ────────────────────────────────────────
    from app.services.admin_notify import notify_admin_telegram
    _plan_name = plan_info.get("name") or data.plan
    _coupon_line = (
        f"🏷️ كوبون: <code>{coupon.code}</code> (−{coupon.discount_percent:g}% من "
        f"${plan_info['price_usd']:g})\n" if coupon else ""
    )
    _msg = (
        f"💳 <b>طلب دفع جديد!</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📧 المستخدم: <code>{user.email}</code>\n"
        f"📦 الباقة: {_plan_name}\n"
        f"{_coupon_line}"
        f"💰 المبلغ: ${final_price:g} USDT\n"
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
    cfg = _stripe_config(db)
    if not cfg["enabled"] or not cfg["secret_key"]:
        raise HTTPException(500, "الدفع بالبطاقة غير متاح حالياً")

    plan_info, final_price, coupon = _priced(db, data.plan, data.coupon_code, user.id)

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": f"Qaffel AI — {plan_info['name_en']} Plan"},
                    "unit_amount": int(round(final_price * 100)),
                },
                "quantity": 1,
            }],
            success_url=cfg["success_url"],
            cancel_url=cfg["cancel_url"],
            client_reference_id=str(user.id),
            customer_email=user.email,
            metadata={"user_id": str(user.id), "plan": data.plan,
                      "coupon": coupon.code if coupon else ""},
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
    cfg = _stripe_config(db)
    if not cfg["enabled"] or not cfg["secret_key"]:
        raise HTTPException(500, "الدفع بالبطاقة غير متاح حالياً")

    plan_info, final_price, coupon = _priced(db, data.plan, data.coupon_code, user.id)

    try:
        intent = stripe.PaymentIntent.create(
            amount=int(round(final_price * 100)),
            currency="usd",
            automatic_payment_methods={"enabled": True},
            receipt_email=user.email,
            description=f"Qaffel AI — {plan_info['name_en']} Plan",
            metadata={"user_id": str(user.id), "plan": data.plan,
                      "coupon": coupon.code if coupon else ""},
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
            coupon_code=metadata.get("coupon") or None,
            amount_cents=session.get("amount_total"),
        )

    elif event["type"] == "payment_intent.succeeded":
        # نموذج البطاقة المدمج بالصفحة (Stripe Elements) — بدون تحويل خارجي
        intent   = event["data"]["object"]
        metadata = intent.get("metadata") or {}
        _finalize_stripe_payment(
            db, background_tasks,
            user_id=metadata.get("user_id"), plan_key=metadata.get("plan"),
            tx_id=intent["id"], payment_intent_id=intent["id"],
            coupon_code=metadata.get("coupon") or None,
            amount_cents=intent.get("amount_received") or intent.get("amount"),
        )

    return {"received": True}


def _finalize_stripe_payment(
    db: Session, background_tasks: BackgroundTasks,
    user_id: Optional[str], plan_key: Optional[str],
    tx_id: str, payment_intent_id: Optional[str],
    coupon_code: Optional[str] = None,
    amount_cents: Optional[int] = None,
) -> None:
    """Shared activation logic for both the hosted-Checkout and embedded
    PaymentIntent flows — idempotent on `tx_id` since Stripe may retry events."""
    if not user_id or plan_key not in PLANS:
        logger.warning(f"⚠️ Stripe webhook missing/invalid metadata: user_id={user_id} plan={plan_key}")
        return

    if db.query(Payment).filter(Payment.tx_id == tx_id).first():
        return

    plan_info = _resolve_plans(db)[plan_key]

    # (2026-09-16) المبلغ يُؤخذ مما حصّلته Stripe فعلاً لا من سعر الباقة:
    # مع الكوبون يختلفان، وتسجيل السعر المعلن كان سيضخّم الإيراد بالتقارير
    # ويحسب عمولة المسوّق على مبلغ لم يُقبض.
    charged = (round(amount_cents / 100.0, 2)
               if amount_cents is not None else float(plan_info["price_usd"]))
    _coupon = find_coupon(db, coupon_code) if coupon_code else None

    payment = Payment(
        user_id     = int(user_id),
        plan        = PaymentPlan(plan_key),
        amount_usd  = charged,
        coupon_code      = _coupon.code if _coupon else None,
        discount_percent = _coupon.discount_percent if _coupon else None,
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
        _plan_name = plan_info.get("name") or plan_key
        _msg = (
            f"💳 <b>دفعة Stripe جديدة (مفعّلة تلقائياً)!</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📧 المستخدم: <code>{user.email}</code>\n"
            f"📦 الباقة: {_plan_name}\n"
            f"💰 المبلغ: ${charged:g}"
            + (f" (كوبون {_coupon.code} −{_coupon.discount_percent:g}%)" if _coupon else "")
            + "\n"
            f"🆔 Payment ID: {payment.id}"
        )
        background_tasks.add_task(notify_admin_telegram, _msg)


def _fetch_spaceremit_payment_info(secret_key: str, payment_id: str) -> dict:
    """POST إلى payment_info مع الـprivate key — يُستخدم لكل من /verify والـwebhook
    كي لا نثق أبداً بأي بيانات دفع قادمة من العميل أو من جسم الـwebhook مباشرة."""
    resp = requests.post(
        SPACEREMIT_API_URL,
        json={"private_key": secret_key, "payment_id": payment_id},
        timeout=15,
    )
    return resp.json()


def _finalize_spaceremit_payment(
    db: Session, background_tasks: BackgroundTasks,
    user_id: int, plan_key: str, info: dict,
    coupon_code: Optional[str] = None,
) -> Payment:
    """منطق تفعيل مشترك بين /spaceremit/verify (يستدعيه الفرونت) والـwebhook
    (يستدعيه Spaceremit من طرف السيرفر) — idempotent على tx_id لأن كلاهما
    قد يصلا لنفس الدفعة."""
    tx_id = info["id"]

    existing = db.query(Payment).filter(Payment.tx_id == tx_id).first()
    if existing:
        return existing

    plan_info = _resolve_plans(db)[plan_key]

    # نفس مبدأ Stripe: المبلغ من الدفعة المحصَّلة لا من سعر الباقة المعلن،
    # وإلا ضُخّم الإيراد وحُسبت عمولة المسوّق على مبلغ لم يُقبض.
    try:
        charged = round(float(info.get("total_amount") or plan_info["price_usd"]), 2)
    except (TypeError, ValueError):
        charged = float(plan_info["price_usd"])
    _coupon = find_coupon(db, coupon_code) if coupon_code else None

    payment = Payment(
        user_id     = user_id,
        plan        = PaymentPlan(plan_key),
        amount_usd  = charged,
        coupon_code      = _coupon.code if _coupon else None,
        discount_percent = _coupon.discount_percent if _coupon else None,
        network     = "spaceremit",
        provider    = "spaceremit",
        tx_id       = tx_id,
        status      = PaymentStatus.APPROVED,
        admin_note  = f"spaceremit status_tag={info.get('status_tag')}",
    )
    db.add(payment)
    db.flush()

    user = activate_subscription_payment(db, payment, background_tasks)
    db.commit()

    if user:
        logger.info(f"💳 Spaceremit payment finalized: user={user.email} plan={plan_key} tx={tx_id}")
        from app.services.admin_notify import notify_admin_telegram
        _plan_name = plan_info.get("name") or plan_key
        _msg = (
            f"💳 <b>دفعة Spaceremit جديدة (مفعّلة تلقائياً)!</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📧 المستخدم: <code>{user.email}</code>\n"
            f"📦 الباقة: {_plan_name}\n"
            f"💰 المبلغ: ${charged:g}"
            + (f" (كوبون {_coupon.code} −{_coupon.discount_percent:g}%)" if _coupon else "")
            + "\n"
            f"🆔 Payment ID: {payment.id}"
        )
        background_tasks.add_task(notify_admin_telegram, _msg)

    return payment


def _validate_spaceremit_info(info: dict, plan_key: str, cfg: dict, db: Session,
                              expected_price: Optional[float] = None) -> Optional[str]:
    """يرجّع رسالة الخطأ لو الدفعة غير صالحة للتفعيل، أو None لو صالحة."""
    tx_id      = info.get("id")
    status_tag = info.get("status_tag")
    accepted_tags = SPACEREMIT_ACCEPTED_TAGS | ({"T"} if cfg["test_mode"] else set())

    if not tx_id or status_tag not in accepted_tags:
        return "لم يتم تأكيد الدفع بعد"
    if info.get("currency") != "USD":
        return "عملة غير متطابقة"
    try:
        paid_amount = float(info.get("total_amount", 0))
    except (TypeError, ValueError):
        paid_amount = 0.0
    # (2026-09-16) المقارنة بالسعر بعد الخصم. لولا ذلك لرُفضت كل دفعة
    # بكوبون: العميل يدفع المخفَّض والخادم ينتظر المعلن.
    plan_info = _resolve_plans(db)[plan_key]
    expected = float(expected_price if expected_price is not None else plan_info["price_usd"])
    if paid_amount + 0.01 < expected:
        return "المبلغ المدفوع غير مطابق للباقة"
    return None


@router.post("/spaceremit/verify")
def verify_spaceremit_payment(
    data: SpaceremitVerifyIn,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """يُستدعى من الفرونت‌إند بعد SP_SUCCESSFUL_PAYMENT(code) — لا نثق بالكود القادم
    من العميل مباشرة، نتحقق منه من طرف السيرفر عبر payment_info قبل تفعيل الاشتراك.
    هذا هو مسار التفعيل الأساسي والفوري؛ الـwebhook بالأسفل شبكة أمان إضافية."""
    plan_info, expected_price, coupon = _priced(db, data.plan, data.coupon_code, user.id)

    cfg = _spaceremit_config(db)
    if not cfg["enabled"] or not cfg["secret_key"]:
        raise HTTPException(500, "الدفع عبر Spaceremit غير متاح حالياً")

    try:
        payload = _fetch_spaceremit_payment_info(cfg["secret_key"], data.spaceremit_code)
    except Exception as e:
        logger.error(f"❌ Spaceremit verify request error: {e}")
        raise HTTPException(502, "تعذّر التحقق من الدفع، حاول لاحقاً")

    if payload.get("response_status") != "success":
        raise HTTPException(400, payload.get("message") or "فشل التحقق من الدفع")

    info = payload.get("data") or {}
    err  = _validate_spaceremit_info(info, data.plan, cfg, db, expected_price)
    if err:
        raise HTTPException(400, err)

    payment = _finalize_spaceremit_payment(
        db, background_tasks, user.id, data.plan, info,
        coupon_code=coupon.code if coupon else None,
    )
    return {"success": True, "payment_id": payment.id}


@router.post("/spaceremit/webhook")
async def spaceremit_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """عنوان الـcallback الذي يُدخَل بلوحة Spaceremit (Websites And Keys).
    شبكة أمان إضافية فقط — التفعيل الفعلي يتم عادة عبر /spaceremit/verify فور
    نجاح الدفع بالفرونت. لا نثق بجسم الطلب القادم من الشبكة مباشرة: نعيد
    الاستعلام عن الدفعة بمفتاحنا السري قبل أي تفعيل. الرد دائماً 200 لتفادي
    إعادة محاولات Spaceremit اللانهائية على حالات نتجاهلها عمداً."""
    try:
        body = await request.json()
    except Exception:
        return {"received": True}

    payment_id = ((body.get("data") or {}).get("id")) or body.get("id") or body.get("payment_id")
    if not payment_id:
        return {"received": True}

    cfg = _spaceremit_config(db)
    if not cfg["secret_key"]:
        return {"received": True}

    try:
        payload = _fetch_spaceremit_payment_info(cfg["secret_key"], payment_id)
    except Exception as e:
        logger.error(f"❌ Spaceremit webhook verify error: {e}")
        return {"received": True}

    if payload.get("response_status") != "success":
        return {"received": True}

    info  = payload.get("data") or {}
    notes = info.get("notes") or ""
    fields = dict(part.split("=", 1) for part in notes.split(";") if "=" in part)
    user_id_raw = fields.get("uid")
    plan_key    = fields.get("plan")

    if not user_id_raw or plan_key not in PLANS:
        logger.warning(f"⚠️ Spaceremit webhook: could not resolve user/plan from notes={notes!r}")
        return {"received": True}

    # (2026-09-16) الكوبون يصل عبر notes مثل uid/plan. بدونه يرفض الويبهوك
    # كل دفعة مخفَّضة: المبلغ المحصَّل أقل من السعر المعلن. والاعتماد على
    # notes هنا مقبول لأن الرمز يُتحقَّق منه بـvalidate_coupon كأي مسار
    # آخر، والكوبونات رموز عامة أصلاً — والمسار الأساسي للتفعيل هو
    # /spaceremit/verify الموثَّق، وهذا شبكة أمان.
    from app.services.coupon_service import validate_coupon, apply_discount
    _cp_code = fields.get("coupon") or None
    _cp, _ = validate_coupon(db, _cp_code, plan_key, int(user_id_raw) if user_id_raw.isdigit() else None)
    _expected = apply_discount(_resolve_plans(db)[plan_key]["price_usd"], _cp)

    if _validate_spaceremit_info(info, plan_key, cfg, db, _expected):
        return {"received": True}

    try:
        _finalize_spaceremit_payment(
            db, background_tasks, int(user_id_raw), plan_key, info,
            coupon_code=_cp.code if _cp else None,
        )
    except Exception as e:
        logger.error(f"❌ Spaceremit webhook finalize error: {e}")

    return {"received": True}


@router.post("/paypal/create-order")
def create_paypal_order(
    data: PayPalOrderIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """يُنشئ Order بـPayPal بسعر من نقطة التسعير الموحّدة (_priced) — نفس
    قاعدة الكوبونات المطبَّقة على كل مسار دفع آخر. الفرونت يستخدم order_id
    مع حقول البطاقة المستضافة (بلا شعار PayPal)، ثم يستدعي /capture-order."""
    cfg = _paypal_config(db)
    if not cfg["enabled"] or not cfg["client_id"] or not cfg["secret_key"]:
        raise HTTPException(500, "الدفع بالبطاقة غير متاح حالياً")

    plan_info, final_price, coupon = _priced(db, data.plan, data.coupon_code, user.id)

    try:
        token = _paypal_access_token(cfg)
        resp = requests.post(
            f"{cfg['base_url']}/v2/checkout/orders",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "intent": "CAPTURE",
                "purchase_units": [{
                    "amount": {"currency_code": "USD", "value": f"{final_price:.2f}"},
                    "custom_id": _paypal_custom_id(user.id, data.plan, coupon.code if coupon else None),
                    "description": f"Qaffel AI — {plan_info['name_en']} Plan",
                }],
            },
            timeout=15,
        )
        resp.raise_for_status()
        order = resp.json()
    except Exception as e:
        logger.error(f"❌ PayPal create order error: {e}")
        raise HTTPException(500, "تعذّر تجهيز الدفع بالبطاقة، حاول لاحقاً")

    return {"order_id": order["id"], "client_id": cfg["client_id"]}


@router.post("/paypal/capture-order")
def capture_paypal_order(
    data: PayPalCaptureIn,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """يُستدعى من الفرونت فور نجاح CardFields.submit() — التفعيل الفعلي
    يتم هنا مباشرة (نفس مبدأ /spaceremit/verify)، لا بانتظار الويبهوك.
    لا نثق بـorder_id وحده: نتحقق إن custom_id المرفَق بالطلب (مُثبَّت
    وقت الإنشاء من طرف الخادم) يخصّ نفس المستخدم المصادَق عليه قبل أي
    تفعيل — وإلا لأمكن لأي مستخدم تمرير order_id شخص آخر."""
    cfg = _paypal_config(db)
    if not cfg["enabled"] or not cfg["client_id"] or not cfg["secret_key"]:
        raise HTTPException(500, "الدفع بالبطاقة غير متاح حالياً")

    try:
        token = _paypal_access_token(cfg)
        resp = requests.post(
            f"{cfg['base_url']}/v2/checkout/orders/{data.order_id}/capture",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "PayPal-Request-Id": f"capture-{data.order_id}",  # مفتاح idempotency لدى PayPal نفسها
            },
            timeout=20,
        )
    except Exception as e:
        logger.error(f"❌ PayPal capture request error: {e}")
        raise HTTPException(502, "تعذّر تأكيد الدفع، حاول لاحقاً")

    if resp.status_code not in (200, 201):
        logger.warning(f"⚠️ PayPal capture failed order={data.order_id}: {resp.status_code} {resp.text}")
        raise HTTPException(400, "فشل تنفيذ الدفع — تحقق من بيانات البطاقة")

    result = resp.json()
    if result.get("status") != "COMPLETED":
        raise HTTPException(400, "لم يكتمل الدفع بعد، حاول مرة أخرى")

    pu = (result.get("purchase_units") or [{}])[0]
    captures = ((pu.get("payments") or {}).get("captures") or [])
    if not captures:
        raise HTTPException(400, "تعذّر تأكيد الدفع")
    capture = captures[0]

    owner_id, plan_key, cp_code = _parse_paypal_custom_id(pu.get("custom_id") or "")
    if owner_id != user.id or plan_key not in PLANS:
        logger.warning(
            f"⚠️ PayPal capture ownership mismatch: order={data.order_id} "
            f"custom_id={pu.get('custom_id')!r} auth_user={user.id}"
        )
        raise HTTPException(403, "هذا الطلب لا يخصّك")

    charged = float(((capture.get("amount") or {}).get("value")) or 0)

    payment = _finalize_paypal_payment(
        db, background_tasks, user.id, plan_key, capture["id"], charged,
        coupon_code=cp_code,
    )
    return {"success": True, "payment_id": payment.id}


@router.post("/paypal/webhook")
async def paypal_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """شبكة أمان فقط — التفعيل الفعلي عبر /paypal/capture-order أعلاه.
    لا نثق بجسم الويبهوك بلا تحقق توقيع من PayPal نفسها؛ بلا webhook_id
    مُعدّ من الداشبورد نتجاهله بأمان بدل تفعيل بلا تحقق. الرد دائماً 200
    لتفادي إعادة محاولات PayPal اللانهائية على حالات نتجاهلها عمداً."""
    try:
        body = await request.json()
    except Exception:
        return {"received": True}

    if body.get("event_type") != "PAYMENT.CAPTURE.COMPLETED":
        return {"received": True}

    cfg = _paypal_config(db)
    if not cfg["webhook_id"] or not cfg["client_id"] or not cfg["secret_key"]:
        return {"received": True}

    try:
        token = _paypal_access_token(cfg)
        verify_resp = requests.post(
            f"{cfg['base_url']}/v1/notifications/verify-webhook-signature",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "transmission_id":   request.headers.get("paypal-transmission-id", ""),
                "transmission_time": request.headers.get("paypal-transmission-time", ""),
                "cert_url":          request.headers.get("paypal-cert-url", ""),
                "auth_algo":         request.headers.get("paypal-auth-algo", ""),
                "transmission_sig":  request.headers.get("paypal-transmission-sig", ""),
                "webhook_id":        cfg["webhook_id"],
                "webhook_event":     body,
            },
            timeout=15,
        )
        if verify_resp.json().get("verification_status") != "SUCCESS":
            logger.warning("⚠️ PayPal webhook signature verification failed")
            return {"received": True}
    except Exception as e:
        logger.error(f"❌ PayPal webhook verify error: {e}")
        return {"received": True}

    resource   = body.get("resource") or {}
    capture_id = resource.get("id")
    owner_id, plan_key, cp_code = _parse_paypal_custom_id(resource.get("custom_id") or "")
    if not capture_id or owner_id is None or plan_key not in PLANS:
        return {"received": True}

    charged = float(((resource.get("amount") or {}).get("value")) or 0)
    try:
        _finalize_paypal_payment(
            db, background_tasks, owner_id, plan_key, capture_id, charged,
            coupon_code=cp_code,
        )
    except Exception as e:
        logger.error(f"❌ PayPal webhook finalize error: {e}")

    return {"received": True}


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


class CouponCheckIn(BaseModel):
    plan: str
    code: str


@router.post("/validate-coupon")
def validate_coupon_endpoint(
    data: CouponCheckIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    معاينة الخصم قبل الدفع. لا يُنشئ شيئاً ولا يحجز الكوبون — العدّاد يزيد
    عند اعتماد الدفعة وحده، وإلا لأمكن استنفاد كوبون محدود بالضغط على زر
    التحقق مراراً.

    يُعيد 200 مع valid=false لا 400: رمز خاطئ حالة متوقعة بواجهة إدخال،
    والخطأ يُعرض في مكانه بالنموذج لا كفشل طلب.
    """
    from app.services.coupon_service import validate_coupon, apply_discount

    plans = _resolve_plans(db)
    if data.plan not in plans:
        raise HTTPException(400, "باقة غير صحيحة")

    plan_info = plans[data.plan]
    base      = float(plan_info["price_usd"])
    coupon, err = validate_coupon(db, data.code, data.plan, user.id)

    if err or not coupon:
        return {"valid": False, "error": err or "رمز الخصم غير صحيح",
                "price_before": base, "price_after": base}

    after = apply_discount(base, coupon)
    return {
        "valid":            True,
        "code":             coupon.code,
        "discount_percent": coupon.discount_percent,
        "price_before":     base,
        "price_after":      after,
        "saved":            round(base - after, 2),
    }
