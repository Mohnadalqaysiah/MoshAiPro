"""
Mosh AI Pro v5 - Bot API
Endpoints خاصة بالبوت (تتحقق من BOT_SECRET بدلاً من JWT المستخدم)
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
from loguru import logger

from app.database import get_db
from app.models.user import User, PlanType
from app.models.signal import Signal, SignalStatus
from app.services.ai_engine_v5 import mosh_ai_engine_v5
from app.services.smart_data import smart_data as _smart_data
from app.config import get_settings

router = APIRouter()
settings = get_settings()


def verify_bot(x_bot_secret: Optional[str] = Header(None)):
    """التحقق من سر البوت"""
    if x_bot_secret != settings.BOT_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized bot request")
    return True


def _get_linked_user(telegram_id: str, db: Session) -> Optional[User]:
    """يجلب المستخدم المرتبط بهذا telegram_id"""
    return db.query(User).filter(
        User.telegram_id == telegram_id,
        User.is_active == True,
        User.plan != PlanType.BANNED,
    ).first()


@router.post("/analyze")
async def bot_analyze(
    symbol: str,
    timeframe: str = "1h",
    telegram_id: str = "",
    _: bool = Depends(verify_bot),
    db: Session = Depends(get_db),
):
    """
    تحليل من البوت - يتحقق أن المستخدم مرتبط وله اشتراك نشط
    telegram_id: اختياري، إذا أُرسل يتحقق من الاشتراك
    """
    # إذا أُرسل telegram_id → تحقق من الاشتراك
    if telegram_id:
        user = _get_linked_user(telegram_id, db)
        if not user:
            raise HTTPException(403, "الحساب غير مرتبط بالمنصة")

        from app.services.auth_service import check_subscription
        status = check_subscription(user, db)
        if not status["allowed"]:
            raise HTTPException(403, status["reason"])

        # خصم كريدت للتجربة
        if user.plan == PlanType.TRIAL and user.trial_analyses_left > 0:
            from app.services.auth_service import deduct_trial
            deduct_trial(user, db, kind="analysis")

    try:
        analysis = await mosh_ai_engine_v5.analyze_market(symbol=symbol, timeframe=timeframe, force_refresh=False)
        return {"success": True, "data": analysis}
    except Exception as e:
        logger.error(f"Bot analyze error: {e}")
        raise HTTPException(500, str(e))


@router.get("/user-status")
def bot_user_status(
    telegram_id: str,
    _: bool = Depends(verify_bot),
    db: Session = Depends(get_db),
):
    """يرجع حالة المستخدم للبوت"""
    user = _get_linked_user(telegram_id, db)
    if not user:
        return {"linked": False}

    from app.services.auth_service import check_subscription
    status = check_subscription(user, db)

    return {
        "linked": True,
        "plan": user.plan,
        "allowed": status["allowed"],
        "reason": status.get("reason", ""),
        "trial_analyses_left": user.trial_analyses_left,
        "trial_chat_left": user.trial_chat_left,
        "full_name": user.full_name or user.email,
    }


@router.get("/expiring-soon")
def bot_expiring(
    days: int = 2,
    _: bool = Depends(verify_bot),
    db: Session = Depends(get_db),
):
    """يرجع المستخدمين الذين اشتراكهم ينتهي قريباً"""
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    deadline = now + timedelta(days=days)

    paid_expiring = db.query(User).filter(
        User.plan.in_([PlanType.WEEKLY, PlanType.MONTHLY]),
        User.subscription_ends_at != None,
        User.subscription_ends_at <= deadline,
        User.telegram_id != None,
        User.is_active == True,
    ).all()

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
            days_left = max(0, (u.subscription_ends_at - now).days)
        elif u.trial_ends_at:
            days_left = max(0, (u.trial_ends_at - now).days)
        result.append({
            "telegram_id": u.telegram_id,
            "full_name": u.full_name or u.email,
            "plan": u.plan,
            "days_left": days_left,
        })

    return {"users": result, "count": len(result)}


@router.get("/check-outcomes")
async def bot_check_outcomes(
    _: bool = Depends(verify_bot),
    db: Session = Depends(get_db),
):
    """
    يفحص كل الإشارات النشطة ويعيد أي منها ضرب TP/SL.
    يستخدمه البوت للإشعارات التلقائية بالنتائج.
    """
    now = datetime.now(timezone.utc)
    active = db.query(Signal).filter(
        Signal.status == SignalStatus.ACTIVE,
        Signal.expires_at > now,
    ).all()

    triggered = []
    for sig in active:
        try:
            price_info = await _smart_data.get_realtime_price_with_meta(sig.market)
            price = price_info.get("price") if price_info else None
            if not price:
                continue
            price  = float(price)
            entry  = float(sig.entry_price)
            sl     = float(sig.stop_loss)
            tp1    = float(sig.take_profit_1)
            tp2    = float(sig.take_profit_2)
            is_buy = sig.signal_type.value == "BUY"

            new_status = None
            if is_buy:
                if   price <= sl:  new_status = SignalStatus.SL_HIT
                elif price >= tp2: new_status = SignalStatus.TP2_HIT
                elif price >= tp1: new_status = SignalStatus.TP1_HIT
            else:
                if   price >= sl:  new_status = SignalStatus.SL_HIT
                elif price <= tp2: new_status = SignalStatus.TP2_HIT
                elif price <= tp1: new_status = SignalStatus.TP1_HIT

            if new_status and new_status != sig.status:
                sig.status = new_status
                sig.current_price = price
                db.commit()

                if new_status == SignalStatus.SL_HIT:
                    pnl = -round(abs(entry - sl), 5)
                elif new_status == SignalStatus.TP2_HIT:
                    pnl = round(abs(tp2 - entry), 5)
                else:
                    pnl = round(abs(tp1 - entry), 5)

                user = db.query(User).filter(User.id == sig.user_id).first()
                if user and user.telegram_id:
                    triggered.append({
                        "telegram_id":  user.telegram_id,
                        "signal_id":    sig.id,
                        "market":       sig.market,
                        "timeframe":    sig.timeframe,
                        "signal_type":  sig.signal_type.value,
                        "status":       new_status.value,
                        "entry":        entry,
                        "sl":           sl,
                        "tp1":          tp1,
                        "tp2":          tp2,
                        "current_price":price,
                        "pnl_points":   pnl,
                        "confidence":   sig.ai_confidence,
                    })
        except Exception as _e:
            logger.warning(f"check_outcomes signal {sig.id}: {_e}")

    return {"triggered": triggered, "count": len(triggered)}


@router.get("/watchlist")
def bot_get_watchlist(
    telegram_id: str,
    _: bool = Depends(verify_bot),
    db: Session = Depends(get_db),
):
    """يرجع إعدادات المراقبة المحفوظة في DB للمستخدم المرتبط بالتيليجرام"""
    user = _get_linked_user(telegram_id, db)
    if not user:
        return {"linked": False, "watchlist": [], "timeframe": "1h", "min_confidence": 65, "notifications_enabled": False}
    return {
        "linked": True,
        "watchlist":           user.notify_watchlist      or [],
        "timeframe":           user.notify_timeframe      or "1h",
        "min_confidence":      user.notify_min_confidence or 65,
        "notifications_enabled": bool(user.notifications_enabled),
    }


@router.get("/all-watchlists")
def bot_all_watchlists(
    _: bool = Depends(verify_bot),
    db: Session = Depends(get_db),
):
    """كل المستخدمين الذين لديهم قائمة مراقبة مفعّلة — يستخدمها البوت للإشعارات"""
    users = db.query(User).filter(
        User.telegram_id != None,
        User.notifications_enabled == True,
        User.is_active == True,
        User.plan != PlanType.BANNED,
    ).all()
    result = []
    for u in users:
        wl = u.notify_watchlist or []
        if wl:
            result.append({
                "telegram_id":    u.telegram_id,
                "watchlist":      wl,
                "timeframe":      u.notify_timeframe      or "1h",
                "min_confidence": u.notify_min_confidence or 65,
            })
    return {"users": result, "count": len(result)}
