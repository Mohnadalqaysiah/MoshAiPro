"""
Mosh AI Pro v5 - Bot API
Endpoints خاصة بالبوت (تتحقق من BOT_SECRET بدلاً من JWT المستخدم)
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Header, Body
from sqlalchemy.orm import Session
from typing import Optional
from loguru import logger

from app.database import get_db
from app.models.user import User, PlanType
from app.models.signal import Signal, SignalStatus
from app.models.site_settings import SiteSettings
from app.services.ai_engine_v5 import mosh_ai_engine_v5
from app.services.smart_data import smart_data as _smart_data
from app.config import get_settings


def _pnl_for_outcome(entry: float, exit_price: float, sl: float, tp1: float, tp2: float,
                     market: str, is_buy: bool, status: SignalStatus):
    """
    يحسب PnL الفعلي للإشارة عند إغلاقها.
    يُعيد: (points, pnl_pct, pnl_usd_raw)
    """
    from app.api.admin import _calc_points  # دالة النقاط الموحّدة

    if status == SignalStatus.SL_HIT:
        diff   = abs(entry - sl)
        points = -_calc_points(market, diff)
        ep     = sl
    elif status == SignalStatus.TP2_HIT:
        diff   = abs(tp2 - entry)
        points = _calc_points(market, diff)
        ep     = tp2
    else:  # TP1_HIT
        diff   = abs(tp1 - entry)
        points = _calc_points(market, diff)
        ep     = tp1

    # نسبة الربح/الخسارة
    if is_buy:
        pnl_pct = round((ep - entry) / entry * 100, 3)
    else:
        pnl_pct = round((entry - ep) / entry * 100, 3)

    return round(points, 2), pnl_pct, round(ep, 5)

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

    # رموز المعادن — مستوياتها محفوظة بسعر Spot (بعد basis correction)
    # يجب استخدام نفس مصدر السعر (TV OANDA Spot) للمقارنة الصحيحة
    _SPOT_SYMBOLS = {"XAUUSD", "XAGUSD"}

    triggered = []
    for sig in active:
        try:
            market_upper = sig.market.upper()

            # ── لا تفحص إذا السوق مغلق (إلا الكريبتو) ───────────────────────
            if not _smart_data.is_market_open(sig.market):
                continue

            # ── للمعادن: استخدم TV Spot (نفس مصدر الإشارة) ─────────────────
            if market_upper in _SPOT_SYMBOLS:
                try:
                    from app.services.tv_price_feed import tv_feed
                    tv_p = tv_feed.get_price_sync(market_upper)
                    if tv_p and float(tv_p) > 0:
                        price = float(tv_p)
                    else:
                        # fallback: theoretical carry
                        from app.services.ai_engine_v5 import mosh_ai_engine_v5
                        price_raw, _ = mosh_ai_engine_v5._fetch_spot_price(market_upper)
                        price = float(price_raw) if price_raw > 0 else None
                except Exception:
                    price = None
            else:
                price_info = await _smart_data.get_realtime_price_with_meta(sig.market)
                price = float(price_info["price"]) if price_info and price_info.get("price") else None

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
                is_buy  = sig.signal_type.value == "BUY"
                points, pnl_pct, exit_p = _pnl_for_outcome(
                    entry, price, sl, tp1, tp2, sig.market, is_buy, new_status
                )

                # حفظ النتيجة على الإشارة
                sig.status                  = new_status
                sig.current_price           = price
                sig.points_earned           = points
                sig.profit_loss             = points
                sig.profit_loss_percentage  = pnl_pct
                sig.exit_executed           = datetime.now(timezone.utc)
                db.commit()

                # تحديث performance tracker في المحرك (Task 6)
                perf_result = "WIN" if new_status in (SignalStatus.TP1_HIT, SignalStatus.TP2_HIT) else "LOSS"
                mosh_ai_engine_v5.update_performance(perf_result)
                logger.info(
                    f"Performance updated: {perf_result} | "
                    f"winrate={mosh_ai_engine_v5.get_winrate():.0%}"
                )

                payload = {
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
                    "pnl_points":   points,
                    "pnl_pct":      pnl_pct,
                    "confidence":   sig.ai_confidence,
                }

                # إذا كانت الإشارة مُبثّة لكل المشتركين → نُضيف كل المشتركين
                if sig.broadcast_sent:
                    active_subs = db.query(User).filter(
                        User.telegram_id != None,
                        User.is_active == True,
                        User.plan != PlanType.BANNED,
                    ).all()
                    now_utc = datetime.now(timezone.utc)
                    for sub in active_subs:
                        valid = False
                        if sub.plan in [PlanType.WEEKLY, PlanType.MONTHLY]:
                            valid = sub.subscription_ends_at and sub.subscription_ends_at > now_utc
                        elif sub.plan == PlanType.TRIAL:
                            valid = not sub.trial_ends_at or sub.trial_ends_at > now_utc
                        if valid and sub.telegram_id:
                            triggered.append({"telegram_id": sub.telegram_id, **payload})
                else:
                    # إشارة خاصة بمستخدم واحد
                    user = db.query(User).filter(User.id == sig.user_id).first()
                    if user and user.telegram_id:
                        triggered.append({"telegram_id": user.telegram_id, **payload})
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
    from app.services.auth_service import check_subscription
    users = db.query(User).filter(
        User.telegram_id != None,
        User.notifications_enabled == True,
        User.is_active == True,
        User.plan != PlanType.BANNED,
    ).all()
    result = []
    for u in users:
        wl = u.notify_watchlist or []
        if not wl:
            continue
        # ── تحقق من صلاحية الاشتراك — لا تنبيهات لمن انتهت تجربته ──────
        status = check_subscription(u, db)
        if not status["allowed"]:
            continue
        result.append({
            "telegram_id":    u.telegram_id,
            "watchlist":      wl,
            "timeframe":      u.notify_timeframe      or "1h",
            "min_confidence": u.notify_min_confidence or 65,
        })
    return {"users": result, "count": len(result)}


@router.post("/renew-trials")
def bot_renew_trials(
    _: bool = Depends(verify_bot),
    db: Session = Depends(get_db),
):
    """
    يجدّد الفترة التجريبية لكل مستخدم تجريبي مضى عليه شهر أو أكثر.
    يُستدعى من البوت مرة يومياً.
    القاعدة: إذا trial_renewed_at (أو created_at) < الآن - 30 يوم → تجديد.
    """
    from datetime import timedelta
    now    = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=30)

    # المستخدمون التجريبيون الذين مضى شهر على آخر تجديد (أو على إنشاء الحساب)
    candidates = db.query(User).filter(
        User.plan == PlanType.TRIAL,
        User.is_active == True,
    ).all()

    def _get_setting(key: str, default: int) -> int:
        r = db.query(SiteSettings).filter(SiteSettings.key == key).first()
        try: return int(r.value) if r and r.value else default
        except: return default

    analysis_limit = _get_setting("trial_analysis_limit", 10)
    chat_limit     = _get_setting("trial_chat_limit", 20)

    renewed = []
    for u in candidates:
        last_renewal = u.trial_renewed_at or u.created_at
        if last_renewal and last_renewal < cutoff:
            u.trial_analyses_left = analysis_limit
            u.trial_chat_left     = chat_limit
            u.trial_ends_at       = now + timedelta(days=7)  # 7 أيام جديدة
            u.trial_renewed_at    = now
            renewed.append(u.id)
            logger.info(f"🔄 Trial renewed for user {u.id} ({u.email})")

    if renewed:
        db.commit()

    return {"renewed_count": len(renewed), "user_ids": renewed}


@router.get("/new-signals")
def bot_new_signals(
    _: bool = Depends(verify_bot),
    db: Session = Depends(get_db),
):
    """
    إشارات جديدة لم تُبث بعد (broadcast_sent=False).
    لا تُعيد إشارات للأسواق المغلقة — تمنع البث بسعر قديم/خاطئ.
    """
    signals = db.query(Signal).filter(
        Signal.status == SignalStatus.ACTIVE,
        Signal.broadcast_sent == False,
    ).order_by(Signal.created_at.desc()).limit(20).all()

    # عمر الإشارة الأقصى قبل إلغاء البث (بالدقائق حسب الإطار)
    _MAX_SIGNAL_AGE = {"1m":5,"5m":10,"15m":20,"30m":30,"1h":60,"4h":180,"1d":720}
    now = datetime.now(timezone.utc)

    # الحد الأدنى للثقة للبث — إشارات أضعف من هذا لا ترسل للمشتركين
    _MIN_BROADCAST_CONFIDENCE = 70

    result = []
    for s in signals:
        # ── لا تبث إشارة إذا السوق مغلق (إلا الكريبتو) ──────────────────
        if not _smart_data.is_market_open(s.market):
            continue

        # ── لا تبث إشارة ثقتها أقل من الحد الأدنى ───────────────────────
        sig_conf = float(s.ai_confidence or 0)
        if sig_conf < _MIN_BROADCAST_CONFIDENCE:
            s.broadcast_sent = True
            db.commit()
            logger.info(f"⏭️  Signal #{s.id} [{s.market}] skipped — conf={sig_conf:.0f}% < {_MIN_BROADCAST_CONFIDENCE}%")
            continue

        # ── لا تبث إشارة قديمة (سعرها لم يعد صالحاً) ────────────────────
        if s.created_at:
            age_min = (now - s.created_at).total_seconds() / 60
            max_age = _MAX_SIGNAL_AGE.get(s.timeframe or "1h", 60)
            if age_min > max_age:
                s.broadcast_sent = True
                db.commit()
                logger.info(f"⏭️  Signal #{s.id} [{s.market}/{s.timeframe}] skipped — age {age_min:.0f}min > {max_age}min")
                continue

        result.append({
            "id":             s.id,
            "market":         s.market,
            "timeframe":      s.timeframe,
            "signal_type":    s.signal_type.value,
            "ai_confidence":  s.ai_confidence,
            "entry_price":    s.entry_price,
            "stop_loss":      s.stop_loss,
            "take_profit_1":  s.take_profit_1,
            "take_profit_2":  s.take_profit_2,
            "risk_reward_ratio": s.risk_reward_ratio,
            "wyckoff_phase":  s.wyckoff_phase,
            "premium_discount": s.premium_discount,
        })

    # إزالة التكرار: إشارة واحدة فقط لكل (رمز + إطار + اتجاه)
    seen: set = set()
    deduped = []
    for sig in result:
        key = (sig["market"], sig["timeframe"], sig["signal_type"])
        if key not in seen:
            seen.add(key)
            deduped.append(sig)
        else:
            # علّم المكرر كمُبثّ حتى لا يعود
            dup = db.query(Signal).filter(Signal.id == sig["id"]).first()
            if dup:
                dup.broadcast_sent = True
            db.commit()

    return {"signals": deduped, "count": len(deduped)}


@router.post("/mark-broadcast/{signal_id}")
def bot_mark_broadcast(
    signal_id: int,
    _: bool = Depends(verify_bot),
    db: Session = Depends(get_db),
):
    sig = db.query(Signal).filter(Signal.id == signal_id).first()
    if not sig:
        raise HTTPException(404, "Signal not found")
    sig.broadcast_sent = True
    db.commit()
    return {"success": True}


@router.post("/mark-result-broadcast/{signal_id}")
def bot_mark_result_broadcast(
    signal_id: int,
    _: bool = Depends(verify_bot),
    db: Session = Depends(get_db),
):
    """علامة أن نتيجة الإشارة (TP/SL) قد بُثّت لكل المشتركين"""
    sig = db.query(Signal).filter(Signal.id == signal_id).first()
    if not sig:
        raise HTTPException(404, "Signal not found")
    sig.result_broadcast_sent = True
    db.commit()
    return {"success": True}


@router.get("/active-subscribers")
def bot_active_subscribers(
    _: bool = Depends(verify_bot),
    db: Session = Depends(get_db),
):
    """كل المشتركين النشطين الذين لديهم telegram_id"""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    users = db.query(User).filter(
        User.telegram_id != None,
        User.is_active == True,
        User.plan != PlanType.BANNED,
    ).all()

    result = []
    for u in users:
        if u.plan in [PlanType.WEEKLY, PlanType.MONTHLY]:
            if not u.subscription_ends_at or u.subscription_ends_at < now:
                continue
        elif u.plan == PlanType.TRIAL:
            if u.trial_ends_at and u.trial_ends_at < now:
                continue
        result.append({"telegram_id": u.telegram_id})

    return {"subscribers": result, "count": len(result)}


@router.get("/user-stats")
def bot_user_stats(
    telegram_id: str,
    _: bool = Depends(verify_bot),
    db: Session = Depends(get_db),
):
    """إحصائيات المستخدم للبوت"""
    from sqlalchemy import func as sqlfunc
    user = _get_linked_user(telegram_id, db)
    if not user:
        return {"linked": False}

    closed = [SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT]
    total  = db.query(Signal).filter(Signal.user_id == user.id, Signal.status.in_(closed)).count()
    wins   = db.query(Signal).filter(Signal.user_id == user.id,
                Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT])).count()
    pts    = db.query(sqlfunc.sum(Signal.points_earned)).filter(
                Signal.user_id == user.id,
                Signal.points_earned != None).scalar() or 0.0
    active = db.query(Signal).filter(
                Signal.user_id == user.id,
                Signal.status == SignalStatus.ACTIVE).count()
    best   = db.query(sqlfunc.max(Signal.points_earned)).filter(
                Signal.user_id == user.id,
                Signal.points_earned > 0).scalar() or 0.0
    worst  = db.query(sqlfunc.min(Signal.points_earned)).filter(
                Signal.user_id == user.id,
                Signal.points_earned < 0).scalar() or 0.0

    # آخر 5 صفقات مغلقة
    recent_sigs = (
        db.query(Signal)
        .filter(Signal.user_id == user.id, Signal.status.in_(closed))
        .order_by(Signal.exit_executed.desc())
        .limit(5)
        .all()
    )
    recent = []
    for s in recent_sigs:
        st = s.status.value if hasattr(s.status, "value") else str(s.status)
        icon = "✅" if st in ("TP1_HIT", "TP2_HIT") else "❌"
        recent.append({
            "market":  s.market,
            "type":    s.signal_type.value if hasattr(s.signal_type, "value") else str(s.signal_type),
            "status":  st,
            "icon":    icon,
            "points":  round(s.points_earned or 0, 2),
            "closed_at": s.exit_executed.strftime("%d/%m %H:%M") if s.exit_executed else "",
        })

    aff_count = 0
    if user.affiliate:
        aff_count = len(user.affiliate.referrals)

    plan_label = {"trial":"تجريبي","weekly":"أسبوعي","monthly":"شهري"}.get(
        str(user.plan.value if hasattr(user.plan,"value") else user.plan).lower(), str(user.plan))

    ends_at = None
    if user.plan in [PlanType.WEEKLY, PlanType.MONTHLY] and user.subscription_ends_at:
        ends_at = user.subscription_ends_at.strftime("%d/%m/%Y")
    elif user.trial_ends_at:
        ends_at = user.trial_ends_at.strftime("%d/%m/%Y")

    return {
        "linked":         True,
        "full_name":      user.full_name or user.email,
        "plan_label":     plan_label,
        "ends_at":        ends_at,
        "total_signals":  total,
        "wins":           wins,
        "losses":         total - wins,
        "win_rate":       round(wins / total * 100, 1) if total > 0 else 0.0,
        "total_points":   round(float(pts), 2),
        "active_signals": active,
        "best_trade":     round(float(best), 2),
        "worst_trade":    round(float(worst), 2),
        "recent_trades":  recent,
        "referral_count":    aff_count,
        "affiliate_code":    user.affiliate_code,
        "referral_points":   user.referral_points or 0,
        "trial_analyses_left": user.trial_analyses_left,
        "trial_chat_left":     user.trial_chat_left,
    }


@router.post("/save-alert-signal")
def bot_save_alert_signal(
    telegram_id: str,
    symbol: str,
    timeframe: str,
    signal_type: str,
    entry: float,
    sl: float,
    tp1: float,
    tp2: float,
    confidence: float,
    rr: float = 0.0,
    _: bool = Depends(verify_bot),
    db: Session = Depends(get_db),
):
    """
    يحفظ إشارة التنبيه (watchlist alert) في DB لتتبع PnL تلقائياً.
    broadcast_sent=False → check-outcomes يُرسل النتيجة لهذا المستخدم فقط.
    """
    import hashlib
    from datetime import timedelta
    from app.models.signal import SignalType as ST, SignalQuality

    user = _get_linked_user(telegram_id, db)
    if not user:
        return {"saved": False, "reason": "user not linked"}

    if signal_type not in ("BUY", "SELL"):
        return {"saved": False, "reason": "invalid signal_type"}

    # لا نحفظ إشارة إذا السوق مغلق — السعر قد يكون قديماً
    if not _smart_data.is_market_open(symbol):
        return {"saved": False, "reason": "market_closed"}

    tf_hours   = {"1m": 2, "5m": 4, "15m": 8, "30m": 12, "1h": 24, "4h": 72, "1d": 168}
    expires_at = datetime.now(timezone.utc) + timedelta(hours=tf_hours.get(timeframe, 24))

    sig_hash = hashlib.md5(
        f"{user.id}-{symbol}-{timeframe}-{signal_type}-{entry:.5f}".encode()
    ).hexdigest()

    existing = db.query(Signal).filter(Signal.signal_hash == sig_hash).first()
    if existing:
        return {"saved": False, "reason": "duplicate", "signal_id": existing.id}

    sig = Signal(
        user_id           = user.id,
        market            = symbol,
        timeframe         = timeframe,
        signal_type       = ST(signal_type),
        signal_quality    = SignalQuality.PREMIUM if confidence >= 80 else SignalQuality.STANDARD,
        status            = SignalStatus.ACTIVE,
        entry_price       = round(entry, 5),
        stop_loss         = round(sl, 5),
        take_profit_1     = round(tp1, 5),
        take_profit_2     = round(tp2, 5),
        ai_confidence     = confidence,
        risk_reward_ratio = rr,
        signal_hash       = sig_hash,
        expires_at        = expires_at,
        broadcast_sent    = False,   # إشارة خاصة بهذا المستخدم
    )
    db.add(sig)
    db.commit()
    db.refresh(sig)
    logger.info(f"💾 Alert signal saved: {symbol}/{timeframe} {signal_type} entry={entry:.5f} user={user.id}")
    return {"saved": True, "signal_id": sig.id}


@router.post("/save-watchlist")
def bot_save_watchlist(
    telegram_id: str,
    watchlist: list = Body(...),
    timeframe: str = "1h",
    min_confidence: int = 65,
    notifications_enabled: bool = True,
    _: bool = Depends(verify_bot),
    db: Session = Depends(get_db),
):
    user = _get_linked_user(telegram_id, db)
    if not user:
        raise HTTPException(404, "User not linked")
    user.notify_watchlist       = watchlist
    user.notify_timeframe       = timeframe
    user.notify_min_confidence  = min_confidence
    user.notifications_enabled  = notifications_enabled
    db.commit()
    return {"success": True}
