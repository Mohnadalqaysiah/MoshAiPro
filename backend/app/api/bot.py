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
from app.models.user import User, PlanType, UserRole
from app.models.signal import Signal, SignalStatus, SignalType
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


# ── قاطع أمان: إيقاف مؤقت لزوج/اتجاه بعد خسائر متتالية ──────────────────────
# HTF conflict حالياً "multiplier" مش gate صارم بمحرك التحليل (قرار مصمم
# بقصد لعدم تفويت انعكاسات LTF مشروعة) — يعني ممكن يستمر يرسل نفس الاتجاه
# ضد الترند الأعلى عدة مرات متتالية بسوق متذبذب. هاد القاطع طبقة حماية
# مستقلة عن محرك القرار: يوقف حفظ إشارات جديدة لنفس (الزوج، الاتجاه) لفترة
# تهدئة بعد عدد معيّن من SL_HIT متتالية، بغض النظر عن سبب الخسارة نفسه.
_LOSS_STREAK_LIMIT      = 3   # عدد الخسائر المتتالية اللي تُفعّل القاطع
_LOSS_STREAK_COOLDOWN_H = 6   # ساعات التهدئة قبل السماح بإشارة جديدة بنفس الاتجاه


def _check_loss_streak_breaker(db: Session, symbol: str, signal_type: str) -> Optional[str]:
    """يرجع سبب الرفض (str) لو القاطع مفعّل حالياً على هالزوج/الاتجاه، وإلا None."""
    from app.models.signal import Signal, SignalStatus

    recent = (
        db.query(Signal)
        .filter(Signal.market == symbol, Signal.signal_type == signal_type)
        .order_by(Signal.created_at.desc())
        .limit(_LOSS_STREAK_LIMIT)
        .all()
    )
    if len(recent) < _LOSS_STREAK_LIMIT or any(s.status != SignalStatus.SL_HIT for s in recent):
        return None

    newest = recent[0].created_at
    if newest and newest.tzinfo is None:
        newest = newest.replace(tzinfo=timezone.utc)
    hours_since = (datetime.now(timezone.utc) - newest).total_seconds() / 3600 if newest else 999
    if hours_since >= _LOSS_STREAK_COOLDOWN_H:
        return None

    logger.warning(
        f"⛔ Loss-streak breaker active: {symbol}/{signal_type} — "
        f"{_LOSS_STREAK_LIMIT} consecutive SL_HIT, last {hours_since:.1f}h ago "
        f"(cooldown {_LOSS_STREAK_COOLDOWN_H}h)"
    )
    return "loss_streak_cooldown"


# ── قاطع أمان: منع تكديس صفقات نشطة متعددة بنفس (رمز، اتجاه، فريم) ──────────
# سبب حادثة XAUUSD SELL بتاريخ 17-18/8: /save-alert-signal كانت تمنع بس
# تكرار نفس المستخدم لنفس السعر بالضبط — فسمحت بفتح 3 صفقات SELL نشطة
# بنفس الوقت على XAUUSD/1h خلال أقل من ساعة، قبل ما أي وحدة منهم تتحدد،
# فـ_check_loss_streak_breaker (اللي بيعتمد على SL_HIT مسجّل فعلياً) ما
# كان عنده معلومة كافية ليمنع.
#
# الفريم جزء من المفتاح عمداً (Phase 5, 2026-08-14): XAUUSD SELL/1h و
# XAUUSD SELL/4h قرارين مستقلين تماماً بمحرك التحليل — لازم يبقوا مسموحين
# بنفس الوقت. بس صفقتين معاً (بأي اتجاه) على نفس (الرمز، الفريم) ممنوعة.
#
# (2026-08-21) الاتجاه (signal_type) اتشال من شرط الفلترة عمداً — لكشف
# تحقق حي (انظر تحليل XAGUSD/15m لـ18-20/8) إنه ما كان في أي منع بين
# BUY وSELL معاكسين على نفس (رمز، فريم)، رغم إنهم كانوا يُعاملوا كمفتاحين
# منفصلين بالكامل. عرض BUY وSELL بنفس الوقت على نفس (رمز، فريم) تناقض
# منطقي يضرّ بمصداقية المنصة، وأي انعكاس حقيقي بيتحل لحاله بسرعة عبر
# الـSL نفسه — فما في خسارة فرصة، بس تأخير لحد ما القديمة تتحسم.
def _has_active_signal(db: Session, symbol: str, timeframe: str) -> bool:
    """True لو فيه صفقة نشطة أصلاً بنفس (الرمز، الفريم) — بغض النظر عن
    اتجاهها (BUY أو SELL على حد سواء يمنعون).

    (2026-08-18, hotfix) status=ACTIVE لحاله مش كافي — الانتقال لـEXPIRED
    كسول تماماً (بيصير بس لما نفس المستخدم يفتح /signals/history، انظر
    signals.py:331)، فمعظم الصفوف الـACTIVE بقاعدة البيانات فعلياً منتهية
    الصلاحية من زمان وما حد صفّاها. لازم نتحقق من expires_at بنفسنا هون،
    وإلا الفحص يصير يمنع كل إشارة جديدة تقريباً بسبب صفوف قديمة عالقة —
    اكتُشف مباشرة بعد نشر أول نسخة من هالدالة (78 صف ACTIVE لـBTCUSD/1h/SELL
    لحالها، أغلبها قديم)."""
    from datetime import datetime, timezone
    from app.models.signal import Signal, SignalStatus

    now = datetime.now(timezone.utc)
    return db.query(Signal).filter(
        Signal.market      == symbol,
        Signal.timeframe   == timeframe,
        Signal.status      == SignalStatus.ACTIVE,
        (Signal.expires_at.is_(None)) | (Signal.expires_at > now),
    ).first() is not None


def _user_has_active_signal(db: Session, user_id: int, symbol: str, timeframe: str) -> bool:
    """مثل _has_active_signal، بس مفلترة على مستخدم واحد بالذات — تُستخدم
    حصراً لتنبيهات المراقبة الشخصية (save-alert-signal). الفرق مقصود:
    _has_active_signal (عامة) تمنع تضارب BUY/SELL على مستوى السوق كله
    لضبط تتبّع الأداء، بينما هاي تجيب "هل هالمستخدم بالذات لسا عنده
    صفقة صالحة بنفس الرمز/الفريم؟" — لو نعم، ما نكرر تنبيهه لنفس
    الفرصة طول ما هي مفتوحة (بدل الاعتماد على مؤقّت زمني ثابت، انظر
    2026-08-31 تعليق بـmonitor_watchlists بالبوت)."""
    now = datetime.now(timezone.utc)
    return db.query(Signal).filter(
        Signal.user_id      == user_id,
        Signal.market       == symbol,
        Signal.timeframe    == timeframe,
        Signal.status       == SignalStatus.ACTIVE,
        (Signal.expires_at.is_(None)) | (Signal.expires_at > now),
    ).first() is not None


@router.post("/analyze")
async def bot_analyze(
    symbol: str,
    timeframe: str = "1h",
    telegram_id: str = "",
    system_user_id: Optional[int] = None,
    _: bool = Depends(verify_bot),
    db: Session = Depends(get_db),
):
    """
    تحليل من البوت - يتحقق أن المستخدم مرتبط وله اشتراك نشط
    telegram_id: اختياري، إذا أُرسل يتحقق من الاشتراك ويُخصم كريدت التجربة
    system_user_id: اختياري — للاستدعاء الداخلي من مهام خلفية (مثل
        market_scanner.py) بلا مستخدم Telegram حقيقي. لا فحص اشتراك ولا
        خصم كريدت، الإشارة المحفوظة تُنسَب لهذا الحساب فقط لغرض FK.

    ✅ الآن يحفظ الإشارات تلقائياً في DB إذا استوفت الشروط!
    """
    # إذا أُرسل telegram_id → تحقق من الاشتراك
    signal_user_id: Optional[int] = system_user_id
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

        signal_user_id = user.id

    try:
        analysis = await mosh_ai_engine_v5.analyze_market(symbol=symbol, timeframe=timeframe, force_refresh=False)
        
        # ✅ حفظ الإشارة تلقائياً إذا استوفت شروط الجودة
        try:
            import hashlib
            from datetime import timedelta
            from app.models.signal import Signal, SignalType, SignalStatus
            from app.services.smart_data import smart_data as _sd
            
            rec    = analysis.get("recommendation", "WAIT")
            levels = analysis.get("levels", {})
            entry  = levels.get("entry")
            sl     = levels.get("stop_loss") or analysis.get("stop_loss_zone")
            tp1    = levels.get("tp1")
            tp2    = levels.get("tp2")
            conf   = analysis.get("ai_confidence_score", 0)
            rr     = levels.get("risk_reward")
            
            _rr_ok  = rr and float(rr) >= 1.2
            _rej    = (analysis.get("validation_rejected") or
                       analysis.get("sweep_gate_blocked") or
                       analysis.get("price_gap_rejected"))
            _cooldown_ok = mosh_ai_engine_v5.check_cooldown(symbol, timeframe)
            
            if rec in ("BUY", "SELL") and entry and sl and tp1 \
                    and conf >= 40 and _rr_ok and not _rej and _cooldown_ok \
                    and analysis.get("market_open", True) and _sd.is_market_open(symbol) \
                    and not _check_loss_streak_breaker(db, symbol, rec) \
                    and not _has_active_signal(db, symbol, timeframe) \
                    and signal_user_id is not None:

                sig_type  = SignalType.BUY if rec == "BUY" else SignalType.SELL
                tf_hours  = {"1m":2,"5m":4,"15m":8,"30m":12,"1h":24,"4h":72,"1d":168,"1w":336}
                expires_h = tf_hours.get(timeframe, 24)
                expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_h)

                sig_hash = hashlib.md5(
                    f"{symbol}-{timeframe}-{rec}-{round(float(entry), 4)}".encode()
                ).hexdigest()
                existing = db.query(Signal).filter(Signal.signal_hash == sig_hash).first()

                if not existing:
                    new_signal = Signal(
                        user_id            = signal_user_id,
                        market             = symbol,
                        timeframe          = timeframe,
                        signal_type        = sig_type,
                        entry_price        = float(entry),
                        stop_loss          = float(sl),
                        take_profit_1      = float(tp1),
                        take_profit_2      = float(tp2) if tp2 else None,
                        risk_reward_ratio  = float(rr) if rr else None,
                        ai_confidence      = float(conf),
                        wyckoff_phase      = analysis.get("wyckoff_phase"),
                        premium_discount   = analysis.get("premium_discount"),
                        signal_hash        = sig_hash,
                        status             = SignalStatus.ACTIVE,
                        expires_at         = expires_at,
                        broadcast_sent     = False,
                        notes              = analysis.get("news_context"),  # سياق إخباري استشاري فقط
                    )
                    db.add(new_signal)
                    db.commit()
                    logger.info(f"💾 Signal saved: {symbol}/{timeframe} {rec} @ {conf:.0f}% confidence (user_id={signal_user_id})")
        except Exception as _se:
            logger.warning(f"Signal save error in bot_analyze: {_se}")
        
        return {"success": True, "data": analysis}
    except Exception as e:
        logger.error(f"Bot analyze error: {e}")
        raise HTTPException(500, str(e))


@router.post("/analyze-multi-tf")
async def bot_analyze_multi_tf(
    symbol: str,
    timeframes: str = "15m,1h,4h",
    _: bool = Depends(verify_bot),
):
    """
    Phase 5 (2026-08-14) — runs the 3-timeframe scan used by watchlist
    monitoring (monitor_watchlists in telegram-bot/bot.py). Each timeframe
    is a fully independent decision (analyze_market_multi_tf() does not
    blend/average across timeframes).

    No auto-save side effect here, unlike /analyze — the caller saves each
    qualifying timeframe result separately via /save-alert-signal, since a
    symbol can have multiple simultaneously-valid signals now (e.g. a real
    1h BUY and a real 4h BUY at once), each tagged by its own timeframe.
    """
    tfs = [t.strip() for t in timeframes.split(",") if t.strip()]
    try:
        results = await mosh_ai_engine_v5.analyze_market_multi_tf(symbol=symbol, timeframes=tfs)
        return {"success": True, "data": results}
    except Exception as e:
        logger.error(f"Bot analyze-multi-tf error: {e}")
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

    # (2026-09-03) نفس القرار (سوق+فريم+نوع+سعر دخول) بينحفظ كصف Signal
    # منفصل لكل مستخدم استلمه — كلهم بيوصلوا لنفس new_status بنفس هالدورة
    # بالضبط (نفس entry/sl/tp، ونفس السعر الحالي المفحوص). بدون هالـset،
    # update_performance() كان بيتصل مرة لكل صف/مستخدم بدل مرة لكل قرار
    # فعلي، فيضخّم winrate المحرك المُستخدم لمعايرة العتبات الحية. راجع
    # app/services/decision_grouping.py للمنطق الكامل المشترك مع تقارير
    # الأداء (نفس المعيار، هون بدل تشغيل تجميع كامل بكل استدعاء).
    from app.services.decision_grouping import decision_key
    _perf_counted_this_cycle: set = set()

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
                        # (2026-09-03) كان في import محلي لـmosh_ai_engine_v5 هون —
                        # بايثون بيعتبر أي اسم مستورد جوا الدالة "محلي" لكل الدالة
                        # كلها (مش بس الفرع هذا)، فبيحجب النسخة العامة المستوردة
                        # فوق (سطر 15) طول الدالة. أي استدعاء لـmosh_ai_engine_v5
                        # قبل ما هالسطر يتنفذ فعلياً بنفس الاستدعاء (زي
                        # update_performance تحت) كان يطلع UnboundLocalError —
                        # مكتوم بصمت بالـexcept العام، فمنعت تسجيل winrate الحي
                        # ونتيجة الصفقة (triggered.append) بالكامل لأي إشارة
                        # تُعالَج قبل أول استخدام فعلي لهالفرع بنفس الدورة.
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

                # تحديث performance tracker في المحرك (Task 6) — مرة وحدة
                # لكل قرار فريد، مو لكل صف/مستخدم (انظر التعليق فوق الحلقة)
                dkey = decision_key(sig.market, sig.timeframe, sig.signal_type, sig.entry_price)
                if dkey not in _perf_counted_this_cycle:
                    _perf_counted_this_cycle.add(dkey)
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
    """كل المستخدمين الذين لديهم قائمة مراقبة مفعّلة — يستخدمها البوت للإشعارات.

    (2026-08-21) كان في تحقق كامل عبر check_subscription هون بيستبعد أي
    مستخدم انتهت تجربته بالكامل — يعني قطع تنبيهات المراقبة الشخصية نهائياً
    عنهم، بعكس القرار المنتجي (نواصل الإرسال، القفل على التفاصيل فقط —
    full_access بيوصل نفس هالمعلومة للبوت زي /active-subscribers). الاستبعاد
    الوحيد المتبقي هو تحقق البريد (is_verified) — هاد حاجز هوية حقيقي، مش
    علاقة بالاشتراك."""
    users = db.query(User).filter(
        User.telegram_id != None,
        User.notifications_enabled == True,
        User.is_active == True,
        User.plan != PlanType.BANNED,
        User.is_verified == True,
    ).all()
    result = []
    for u in users:
        wl = u.notify_watchlist or []
        if not wl:
            continue
        result.append({
            "telegram_id":    u.telegram_id,
            "watchlist":      wl,
            "timeframe":      u.notify_timeframe      or "1h",
            "min_confidence": u.notify_min_confidence or 65,
            "full_access":    _bot_has_full_signal_access(u),
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
    # تُقلل من 70% إلى 40% لتشمل إشارات الفوركس والمعادن والسلع والمؤشرات والسوق الأمريكي
    # (حد الحفظ الأساسي هو 40% — سيُبث جميع الإشارات المحفوظة)
    _MIN_BROADCAST_CONFIDENCE = 40

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

        # (2026-08-31) إشارات المراقبة الشخصية (save-alert-signal) محفوظة
        # بـuser_id المستخدم الحقيقي، وبتوصله أصلاً كـ"تنبيه مراقبة" منفصل
        # (monitor_watchlists). نجيب تلغرام آيدي صاحبها هون عشان نستثنيه من
        # هالبث العام لنفس الإشارة — تجنّباً لتكرار نفس الفرصة عليه مرتين.
        owner_tid = None
        if s.user_id:
            owner = db.query(User.telegram_id).filter(User.id == s.user_id).first()
            owner_tid = owner[0] if owner else None

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
            "news_context":   s.notes,
            "owner_telegram_id": owner_tid,
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


def _bot_has_full_signal_access(u: User) -> bool:
    """أدمن أو مشترك فعلي (أسبوعي/شهري) يشوف كل تفاصيل كل الإشارات دايماً —
    نفس تعريف _has_full_signal_access بـ signals.py، مكرّر هون لأن bot.py
    وsignals.py مسارين مستقلين وما بدنا استيراد دائري."""
    return u.role == UserRole.ADMIN or u.plan in (PlanType.WEEKLY, PlanType.MONTHLY)


@router.get("/active-subscribers")
def bot_active_subscribers(
    _: bool = Depends(verify_bot),
    db: Session = Depends(get_db),
):
    """كل المشتركين اللي عندهم telegram_id، نشطين وغير محظورين — بما فيهم
    التجربة المنتهية (2026-08-21): القرار المنتجي هو الاستمرار ببث الإشارات
    لهم، بس بنسخة ممموّهة (بدون تفاصيل الدخول/SL/TP) بعد استهلاك حصتهم
    اليومية المجانية — نفس مبدأ /signals/latest بالموقع، مش قطع الإشعارات
    نهائياً. full_access بيحدّد للبوت هل يرسل النسخة الكاملة دايماً بلا حاجة
    لاستهلاك أي حصة."""
    users = db.query(User).filter(
        User.telegram_id != None,
        User.is_active == True,
        User.plan != PlanType.BANNED,
    ).all()

    result = [
        {"telegram_id": u.telegram_id, "full_access": _bot_has_full_signal_access(u)}
        for u in users
    ]

    return {"subscribers": result, "count": len(result)}


@router.post("/consume-signal-notification")
def bot_consume_signal_notification(
    telegram_id: str = Body(..., embed=True),
    _: bool = Depends(verify_bot),
    db: Session = Depends(get_db),
):
    """يُستدعى مرة لكل (مستخدم بلا full_access، إشارة مبثوثة) — يقرر هل
    يستلم النسخة الكاملة (ويستهلك من حصته اليومية) أو الممموّهة. الحد
    اليومي من نفس مفتاح SiteSettings المستخدم بـ/signals/latest
    (trial_signal_daily_limit)، 0 = غير محدود."""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        return {"unlocked": False}

    if _bot_has_full_signal_access(user):
        return {"unlocked": True}

    row = db.query(SiteSettings).filter(SiteSettings.key == "trial_signal_daily_limit").first()
    try:
        free_limit = int(row.value) if row and row.value else 3
    except Exception:
        free_limit = 3
    if free_limit <= 0:
        return {"unlocked": True}

    now = datetime.now(timezone.utc)
    if not user.signal_notif_seen_date or user.signal_notif_seen_date.date() != now.date():
        user.signal_notif_seen_today = 0
        user.signal_notif_seen_date  = now

    if user.signal_notif_seen_today >= free_limit:
        return {"unlocked": False}

    user.signal_notif_seen_today += 1
    user.signal_notif_seen_date   = now
    db.commit()
    return {"unlocked": True, "remaining": free_limit - user.signal_notif_seen_today}


@router.get("/user-stats")
def bot_user_stats(
    telegram_id: str,
    _: bool = Depends(verify_bot),
    db: Session = Depends(get_db),
):
    """إحصائيات المستخدم للبوت

    (2026-09-03) نفس مشكلة get_signal_performance بـsignals.py — حتى
    ضمن مستخدم واحد، مراقبة الـwatchlist القديمة (قبل إصلاح 2026-08-31
    اللي ربط التنبيه بصلاحية الصفقة) كانت ممكن تكرر نفس القرار أكتر من
    مرة لنفس المستخدم. total/wins/pts/best/worst محسوبة الآن على مستوى
    القرار الفريد الموثوق (verified_unique_decisions). active يبقى عدّ
    خام — مو ادعاء أداء."""
    from app.services.decision_grouping import verified_unique_decisions

    user = _get_linked_user(telegram_id, db)
    if not user:
        return {"linked": False}

    closed = [SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT]
    closed_raw = db.query(Signal).filter(Signal.user_id == user.id, Signal.status.in_(closed)).all()
    decisions  = verified_unique_decisions(closed_raw)
    decisions.sort(key=lambda d: d["exit_executed"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    total   = len(decisions)
    wins    = sum(1 for d in decisions if d["status"] in ("TP1_HIT", "TP2_HIT"))
    pts     = sum(d["points"] for d in decisions)
    win_pts = [d["points"] for d in decisions if d["points"] > 0]
    loss_pts= [d["points"] for d in decisions if d["points"] < 0]
    best    = max(win_pts, default=0.0)
    worst   = min(loss_pts, default=0.0)
    active  = db.query(Signal).filter(
                Signal.user_id == user.id,
                Signal.status == SignalStatus.ACTIVE).count()

    # آخر 5 قرارات مغلقة
    recent = []
    for d in decisions[:5]:
        icon = "✅" if d["status"] in ("TP1_HIT", "TP2_HIT") else "❌"
        recent.append({
            "market":  d["market"],
            "type":    d["signal_type"],
            "status":  d["status"],
            "icon":    icon,
            "points":  round(d["points"], 2),
            "closed_at": d["exit_executed"].strftime("%d/%m %H:%M") if d["exit_executed"] else "",
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

    loss_streak_reason = _check_loss_streak_breaker(db, symbol, signal_type)
    if loss_streak_reason:
        return {"saved": False, "reason": loss_streak_reason}

    if _user_has_active_signal(db, user.id, symbol, timeframe):
        return {"saved": False, "reason": "duplicate active position, waiting for resolution"}

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
