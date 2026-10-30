"""
Mosh AI Pro v5 - Bot API
Endpoints خاصة بالبوت (تتحقق من BOT_SECRET بدلاً من JWT المستخدم)
"""
from datetime import datetime, timezone, timedelta   # (2026-10-25) timedelta كان مفقوداً ← إجابة التحدّي ترمي NameError
from fastapi import APIRouter, Depends, HTTPException, Header, Body
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from loguru import logger

from app.database import get_db
from app.services.telegram_reach import reachable as _reachable
from app.services.relax_policy import should_drop as should_drop_relaxed
from app.services.tp_ladder import tp3_open_clause
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

    if status == SignalStatus.BREAKEVEN:   # (2026-10-16) خروج على الدخول بعد رسالة التأمين
        return 0.0, 0.0, round(entry, 5)
    if status == SignalStatus.SL_HIT:
        diff   = abs(entry - sl)
        points = -_calc_points(market, diff, entry)
        ep     = sl
    elif status == SignalStatus.TP2_HIT:
        diff   = abs(tp2 - entry)
        points = _calc_points(market, diff, entry)
        ep     = tp2
    else:  # TP1_HIT
        diff   = abs(tp1 - entry)
        points = _calc_points(market, diff, entry)
        ep     = tp1

    # نسبة الربح/الخسارة
    if is_buy:
        pnl_pct = round((ep - entry) / entry * 100, 3)
    else:
        pnl_pct = round((entry - ep) / entry * 100, 3)

    return round(points, 2), pnl_pct, round(ep, 5)

router = APIRouter()


def _extract_str(value, key: str) -> Optional[str]:
    """
    يستخرج نصاً من حقل قد يكون قاموساً (بنية محرك ICT) أو نصاً جاهزاً.
    وُجد بعد اكتشاف أن premium_discount/wyckoff_phase كانا NULL بكل صفوف
    جدول signals (162/162) لأنهما كانا يُقرآن كنصوص وهما ليسا كذلك.
    """
    if value is None:
        return None
    if isinstance(value, dict):
        v = value.get(key)
        return str(v) if v not in (None, "") else None
    return str(value) or None
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
# (2026-10-14) قواعد رفض تُسجَّل صفقاتها المرفوضة بجدول الظل للتعلّم (تجربة صامتة، راجع bot_analyze)
_LEARN_REJECTIONS = ("ZONE_CONFLICT_", "HTF_CONFLICT", "COMMODITY_COUNTER_4H_TREND", "SL_INSIDE_SPREAD_NOISE")

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
            tp3    = levels.get("tp3")   # (2026-10-30) سلّم الأهداف — tp_ladder.py
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
                # (2026-10-03) 15m نزلت من 8 لـ3 ساعات — راجع تعليق
                # bot_save_alert_signal أسفل بنفس الملف للسبب الكامل.
                tf_hours  = {"1m":2,"5m":4,"15m":3,"30m":12,"1h":24,"4h":72,"1d":168,"1w":336}
                expires_h = tf_hours.get(timeframe, 24)
                expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_h)

                sig_hash = hashlib.md5(
                    f"{symbol}-{timeframe}-{rec}-{round(float(entry), 4)}".encode()
                ).hexdigest()
                existing = db.query(Signal).filter(Signal.signal_hash == sig_hash).first()

                # (2026-10-12) كريبتو بالعطلة → جدول الظل فقط، لا صف Signal (لا بث ولا إحصائية)
                from app.services.weekend_policy import crypto_weekend_paused, record_shadow
                from app.services import market_fingerprint
                if crypto_weekend_paused(db, symbol):
                    _shid = record_shadow(db, source="analyze" if telegram_id else "scanner", symbol=symbol,
                                          timeframe=timeframe, signal_type=rec, entry=entry, sl=sl, tp1=tp1,
                                          tp2=tp3 or tp2, confidence=conf, rr=rr, expires_at=expires_at,
                                          user_id=signal_user_id)
                    market_fingerprint.schedule(analysis, symbol, timeframe, rec, shadow_id=_shid)
                elif should_drop_relaxed(db, analysis, symbol):
                    # (2026-10-24) صفقة مخفَّفة وللمنصة صفقة نشطة بعكسها على نفس الرمز — لا إشارتان متضادتان
                    logger.info(f"🔕 RELAXED_CONFLICT {symbol}/{timeframe} {rec} — صفقة معاكسة نشطة، لا حفظ")
                elif not existing:
                    new_signal = Signal(
                        relaxed_rule       = analysis.get("relaxed_rule"),
                        user_id            = signal_user_id,
                        market             = symbol,
                        timeframe          = timeframe,
                        signal_type        = sig_type,
                        entry_price        = float(entry),
                        stop_loss          = float(sl),
                        take_profit_1      = float(tp1),
                        take_profit_2      = float(tp2) if tp2 else None,
                        take_profit_3      = float(tp3) if tp3 else None,
                        risk_reward_ratio  = float(rr) if rr else None,
                        ai_confidence      = float(conf),
                        # (2026-09-15) الحقلان كانا NULL بكل الصفوف (162/162):
                        # analysis["premium_discount"] قاموس {zone,pct,bias}
                        # لا نص، و"wyckoff_phase" غير موجود بجذر التحليل
                        # أصلاً (الطور تحت analysis["wyckoff"]["phase"]).
                        # فقدنا بذلك أهم سياق ICT لتحليل الجودة لاحقاً —
                        # المنطقة وقت الدخول هي نفسها التي تبني عليها
                        # Rule 6 قرارها للذهب.
                        wyckoff_phase      = _extract_str(analysis.get("wyckoff"), "phase"),
                        premium_discount   = _extract_str(analysis.get("premium_discount"), "zone"),
                        # (2026-09-16) نفس العطل بالضبط، مرة ثالثة: تقرير
                        # الجودة أظهر تغطية 0% لـkillzone على 200 قرار —
                        # الحقل موجود بالجدول ولم يُكتب إليه سطر واحد منذ
                        # إنشائه. الجلسة من أهم روافع ICT (المحرك يحسبها
                        # ويستخدمها بـget_kill_zone ويبني عليها الثقة)،
                        # وكنا نحلّل أثرها على عمود فارغ. المفتاح بجذر
                        # التحليل "kill_zone" والقيمة تحت "active_session".
                        killzone           = _extract_str(analysis.get("kill_zone"), "active_session"),
                        signal_hash        = sig_hash,
                        status             = SignalStatus.ACTIVE,
                        expires_at         = expires_at,
                        broadcast_sent     = False,
                        notes              = analysis.get("news_context"),  # سياق إخباري استشاري فقط
                    )
                    db.add(new_signal)
                    db.commit()
                    logger.info(f"💾 Signal saved: {symbol}/{timeframe} {rec} @ {conf:.0f}% confidence (user_id={signal_user_id})")
                    # (2026-10-13) بصمة السوق للتعلم — بالخلفية، لا تؤخر شيئاً
                    market_fingerprint.schedule(analysis, symbol, timeframe, rec, signal_id=new_signal.id)
        except Exception as _se:
            logger.warning(f"Signal save error in bot_analyze: {_se}")

        # (2026-10-14) تجربة صامتة للقواعد التي تمنع الإشارات — الذهب والفضة صامتان لأن
        # ZONE_CONFLICT_SELL_IN_DISCOUNT يمنع كل بيع في سوق هابط (السعر يبقى "رخيصاً"). لا نعرف هل
        # القاعدة تمنع خاسرات أم رابحات، فتُسجَّل الصفقة المرفوضة بجدول الظل (لا تصل لأحد) ويقيّمها
        # shadow_evaluator من الشموع. بمستويات المنتج الحالي (TP1 عند 1R). لا يمسّ المحرك.
        try:
            _pre = analysis.get("_pre_reject_rec")
            _why = str(analysis.get("rejection_reason") or "")
            if _pre in ("BUY", "SELL") and _why.startswith(_LEARN_REJECTIONS) \
                    and signal_user_id is not None and _smart_data.is_market_open(symbol):
                # (2026-10-18) نفس فحص الجهة الحي (_institutional_gate Rule 6) قبل سقف TP1 — بنفس ترتيب المسار الحي.
                # مستويات بُنيت لاتجاه غير اتجاه الرفض تُرفض ولا تُحفظ (راجع app/services/shadow_levels.py).
                from app.services.shadow_levels import normalize_rejected_levels
                _lv, _bad = normalize_rejected_levels(_pre, analysis.get("_pre_reject_levels") or {})
                if _bad:
                    logger.info(f"🌑 SHADOW_LEVELS_REJECTED {_bad}: {_why[:40]} {symbol}/{timeframe} {_pre}")
                if _lv:
                    from datetime import timedelta
                    from app.services.weekend_policy import record_shadow
                    _capped = mosh_ai_engine_v5._cap_tp1({"recommendation": _pre, "levels": _lv}, symbol, timeframe)["levels"]
                    _hrs = {"1m": 2, "5m": 4, "15m": 3, "30m": 12, "1h": 24, "4h": 72, "1d": 168}.get(timeframe, 24)
                    record_shadow(db, source="rejected", reason=_why, symbol=symbol, timeframe=timeframe,
                                  signal_type=_pre, entry=_capped["entry"], sl=_capped["stop_loss"],
                                  tp1=_capped["tp1"], tp2=_capped.get("tp2"), confidence=None,
                                  rr=_capped.get("risk_reward"),
                                  expires_at=datetime.now(timezone.utc) + timedelta(hours=_hrs))
        except Exception as _rs:
            logger.warning(f"rejected-shadow {symbol}/{timeframe}: {_rs}")

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
        _reachable(),
    ).all()

    trial_expired = db.query(User).filter(
        User.plan == PlanType.TRIAL,
        User.trial_ends_at != None,
        User.trial_ends_at <= now,
        User.telegram_id != None,
        User.is_active == True,
        _reachable(),
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


def _expired_wants_result(user, market: str) -> bool:
    """(2026-10-19) منتهي الاشتراك/التجربة: يستلم نتيجة الإشارة العامة إلا إن أوقف الإشعارات، أو خصّص قائمة مراقبة
    لا تشمل الرمز (نفس اتفاقية البث: قائمة فارغة = كل الرموز)."""
    if user.notifications_enabled is False:
        return False
    wl = [s.upper() for s in (user.notify_watchlist or [])]
    return not wl or (market or "").upper() in wl


@router.get("/check-outcomes")
async def bot_check_outcomes(
    range_check: bool = True,
    _: bool = Depends(verify_bot),
    db: Session = Depends(get_db),
):
    """
    يفحص كل الإشارات النشطة ويعيد أي منها ضرب TP/SL.
    يستخدمه البوت للإشعارات التلقائية بالنتائج.

    range_check=True (افتراضي): يجيب أعلى/أدنى سعر بآخر ~2.5 ساعة (5m) ويفحص
      المدى الكامل — يمسك الـwicks اللي ارتدت. مكلف (طلب OHLC لكل رمز).
    range_check=False: يفحص السعر اللحظي فقط (مكاش 30ث) — رخيص، للحلقة
      السريعة (كل ~90ث) اللي هدفها رصد شبه فوري للحالة الشائعة (السعر
      حالياً متجاوز المستوى). الحلقة السريعة تستدعي range_check=True كل
      عدة دورات لتغطية الـwicks.
    """
    now = datetime.now(timezone.utc)

    # (2026-09-24) بلاغ حقيقي مؤكَّد: إشارة شراء فضة (دخول أعلى من السعر
    # اللحظي وقت الإصدار — أمر معلَّق لم يتفعّل) سُجّلت SL_HIT رغم إن السعر
    # ما لمس منطقة الدخول إطلاقاً. السبب الجذري: الحلقة تحت تعامل أي إشارة
    # ACTIVE كصفقة مفتوحة فعلاً من لحظة إصدارها، وتقارن السعر بـSL/TP مباشرة
    # بلا أي تحقق مسبق من "هل تحقق الدخول أصلاً؟". يُصلَح تحت عبر
    # `entry_executed` (عمود موجود بالجدول أصلاً منذ البداية، غير مُستخدَم
    # لحد الآن) — يُسجَّل أول لحظة يُلمس فيها الدخول فعلياً، ولا يُحتسب أي
    # SL/TP قبلها. راجع DECISIONS.md 2026-09-24 لتفصيل الأثر الكامل: عدد
    # مجهول من "الخسائر" التاريخية قد تكون أوامر لم تُفتح إطلاقاً.
    #
    # إشارات انتهت مدتها بلا ما يتحقق دخولها إطلاقاً: "لم تُفتح الصفقة"،
    # لا "خسارة" — تُقفل EXPIRED مباشرة هون (بدل الاعتماد على فحص كسول
    # عند عرض /history لاحقاً، وهو ممكن ما يصير أبداً لإشارة معيّنة).
    expired_untriggered = db.query(Signal).filter(
        Signal.status == SignalStatus.ACTIVE,
        Signal.expires_at <= now,
        Signal.entry_executed.is_(None),
    ).all()
    for _s in expired_untriggered:
        _s.status = SignalStatus.EXPIRED
    if expired_untriggered:
        db.commit()
        logger.info(f"⏰ {len(expired_untriggered)} إشارة انتهت بلا تفعيل دخول → EXPIRED")

    # (2026-10-09) الفجوة التالية المكتشَفة بنفس العائلة: صفقة تفعّل دخولها
    # فعلاً (entry_executed مسجَّل) بس انتهت مدتها بلا ما تصل TP ولا SL —
    # الكتلة فوق تستثنيها عمداً (entry_executed.is_(None) بس)، والاستعلام
    # التالي (active) يستثنيها كمان (expires_at > now) — فتضل ACTIVE للأبد
    # بلا أي مسار يقفلها. integrity_checker.py يكتشف هذي الحالة وينبّه
    # الأدمن فقط، لا يصلحها. نفس معاملة الحالة الشقيقة فوق بالضبط: صفقة
    # بلا نتيجة حاسمة ضمن مدتها الزمنية = EXPIRED (لا ربح ولا خسارة)، لا
    # SL_HIT وهمي — تُستثنى من حساب نسبة الربح بنفس الطريقة، لا نقاط تُسجَّل
    # لها لأنه لم يُحسم أي شيء فعلياً.
    expired_unresolved = db.query(Signal).filter(
        Signal.status == SignalStatus.ACTIVE,
        Signal.expires_at <= now,
        Signal.entry_executed.isnot(None),
    ).all()
    for _s in expired_unresolved:
        _s.status = SignalStatus.EXPIRED
    if expired_unresolved:
        db.commit()
        logger.info(f"⏰ {len(expired_unresolved)} صفقة مفتوحة انتهت مدتها بلا TP/SL → EXPIRED")

    # (2026-10-10، بتفويض صريح) TP1_HIT ضمن مدتها تبقى تحت الرصد بحثاً عن
    # TP2. قبلها كان تسجيل TP1 يُخرج الصفقة من الرصد نهائياً، فكل TP2 يأتي
    # بعد دورة تسجيل TP1 يضيع — تشخيص 2026-10-09 وجد ~200 صف وصل TP2 فعلياً
    # بالشموع ومسجّل TP1. للصف المقفول على TP1: لا ترقية إلا لـTP2، ولمس
    # الستوب بعد TP1 يُنهي الرصد ويُبقي TP1 (راجع _tp1_locked تحت).
    # (2026-10-30) نفس المبدأ درجة أعلى: بلغت الهدف الثاني ولها ثالث ← تبقى تحت الرصد، والثاني مقفل (tp_ladder.py).
    active = db.query(Signal).filter(
        or_(Signal.status.in_([SignalStatus.ACTIVE, SignalStatus.TP1_HIT]), tp3_open_clause(Signal)),
        Signal.expires_at > now,
    ).all()

    # (2026-09-10) بلاغ حقيقي مؤكد: USOIL سجّلت TP2_HIT رغم إن السعر الحقيقي
    # (حساب Exness/MT4 فعلي) كان أوطأ من الـSL نفسه وقتها. السبب: هون كان
    # يستخدم yfinance CL=F (عقد مستقبلي محدد) فقط لغير المعادن، وهو ينحرف
    # عدة دولارات عن سعر الوسيط الحقيقي أحياناً (تحقق مباشر: CL=F تحرك من
    # ~96 إلى ~102 بنفس اليوم بدون أي تفسير سوقي حقيقي — عيّنة بيانات
    # مضطربة). المشروع أصلاً عنده تغذية Spot حقيقية حية عبر TradingView
    # (tv_price_feed.TV_SYMBOL_MAP) لـ20 رمز — كانت مستخدمة هون للذهب/الفضة
    # بس. توسيعها لكل رمز فيها تحل نفس المشكلة لأي رمز تاني بنفس البنية
    # (NAS100/US30/SP500/فوركس رئيسي/كريبتو رئيسي) — وتفسّر جزئياً كمان ليش
    # الرصد التلقائي كان يعمل صح على الفضة تحديداً (المسار الوحيد المستقر)
    # بينما باقي الرموز تعتمد يفينانس/فينهب (عرضة لتقييد معدل الطلبات لما
    # نفحص رموز كتيرة بدورة وحدة — راجع range_check تحت).
    #
    # (2026-09-16) تراجُع جزئي عن التوسيع أعلاه — بقرار صريح من صاحب المنتج.
    # ما كُشف: التوسيع عالج انحراف مصدر السعر، لكنه أنشأ خللاً أشدّ —
    # المستويات (الدخول/الوقف/الأهداف) تُبنى من get_ohlcv (yfinance)، بينما
    # صار الحكم عليها يُقرأ من TV. فصار السؤال "هل بلغ السعر المستوى؟"
    # يُقاس بمسطرة غير التي رُسم بها المستوى، وهو سؤال بلا معنى.
    # الشاهد المقاس: EURUSD #2528 — مسافة وقفها 2.4 نقطة بينما فارق
    # yfinance EURUSD=X عن OANDA:EURUSD ~1.8 نقطة. فاختلاف المصدرين وحده،
    # بلا أي حركة سوق، كفى ليُسجَّل TP2_HIT خلال دقيقة من الإصدار. ونفس
    # النمط على BTCUSD #2521 (Finnhub BINANCE مقابل yfinance BTC-USD).
    # وأثره يتعدّى الأرقام: الإغلاق الكاذب خلال دقيقة يُخرج الإشارة من
    # فلتر ACTIVE قبل دورة البث (BROADCAST_INTERVAL=60 مقابل
    # OUTCOME_CHECK_INTERVAL=90) فلا تصل المستخدمين أصلاً.
    # القاعدة المعتمدة: تُقاس النتيجة بنفس مرجع بناء المستويات.
    #   • المعادن  → مستوياتها تُزاح للفوري بـ_apply_spot_basis، فمرجعها TV ✅
    #   • ما عداها → مستوياتها من get_ohlcv، فمرجعها get_ohlcv ✅
    # الثمن المقبول صراحةً: قد تعود حالات كبلاغ USOIL (10/09) تخالف فيها
    # النتيجة ما يظهر على منصة الوسيط. وذلك لأن الجذر الحقيقي أن المستويات
    # نفسها تُبنى من yfinance — ولا يُعالَج إلا بتغيير مصدر التوليد، وهو
    # يمسّ المحرك ومؤجَّل عمداً. التوسيع كان يضيف خطأ ثانياً فوق الأول لا
    # يرفعه. هذا التعديل يقيس النتيجة لا يولّدها: صفر أثر على الاستراتيجية.
    from app.services.tv_price_feed import TV_SYMBOL_MAP, fetch_tv_history
    _SPOT_SYMBOLS = {"XAUUSD", "XAGUSD"}
    _METALS_ONLY  = {"XAUUSD", "XAGUSD"}   # الوحيدة اللي عندها fallback نظري خاص تحت

    # (2026-09-03) نفس القرار (سوق+فريم+نوع+سعر دخول) بينحفظ كصف Signal
    # منفصل لكل مستخدم استلمه — كلهم بيوصلوا لنفس new_status بنفس هالدورة
    # بالضبط (نفس entry/sl/tp، ونفس السعر الحالي المفحوص). بدون هالـset،
    # update_performance() كان بيتصل مرة لكل صف/مستخدم بدل مرة لكل قرار
    # فعلي، فيضخّم winrate المحرك المُستخدم لمعايرة العتبات الحية. راجع
    # app/services/decision_grouping.py للمنطق الكامل المشترك مع تقارير
    # الأداء (نفس المعيار، هون بدل تشغيل تجميع كامل بكل استدعاء).
    from app.services.decision_grouping import decision_key
    _perf_counted_this_cycle: set = set()

    # (2026-10-01) بلاغ حقيقي: نفس القرار الواحد (محفوظ كصف Signal منفصل
    # لكل مستخدم استلمه) كان يُنتج بثّاً كاملاً مستقلاً لكل صف منه يضرب
    # TP/SL بنفس الدورة — فلو 5 صفوف لنفس القرار انضربت معاً، كل مشترك
    # نشط (يشمل الأدمن) ياخد 5 رسائل نتيجة مطابقة تماماً بدل رسالة وحدة.
    # نفس حل ازدواجية update_performance() فوق (dkey/_perf_counted_this_cycle)
    # يُطبَّق هون: حلقة البث لكل المشتركين تُنفَّذ مرة واحدة فقط لكل قرار
    # فريد بالدورة، لا مرة لكل صف يمثّله.
    _broadcast_fanout_done_this_cycle: set = set()
    from app.services.smart_data import GULF_SYMBOL_MAP as _GULF_MAP
    _gulf_px_cycle: dict = {}   # سعر خليجي واحد لكل رمز بالدورة (عدة صفوف لنفس الرمز)
    _INDEX_FUTURES_REF = {"NAS100", "US30", "SP500"}

    triggered = []
    for sig in active:
        try:
            market_upper = sig.market.upper()

            # ── لا تفحص إذا السوق مغلق (إلا الكريبتو) ───────────────────────
            if not _smart_data.is_market_open(sig.market):
                continue

            # ── السعر اللحظي ───────────────────────────────────────────────
            # (2026-09-16 #3) فُصل مصدر السعر اللحظي عن مصدر شموع المشي.
            # كان _SPOT_SYMBOLS يحكم الاثنين معاً، فلمّا قُصر على المعادن
            # لتصحيح مرجع الشموع، انتقلت بقية الرموز قسراً لمسار السعر
            # العام — وهو ليس ما قُصد. القاعدتان مستقلتان:
            #   • مرجع الشموع يجب أن يطابق مرجع بناء المستويات (معادن فقط).
            #   • مصدر السعر اللحظي يُختار بالإتاحة والكلفة: كاش TV مجاني
            #     ومحدَّث، وأي مسار آخر طلبُ شبكة لكل رمز كل 90 ثانية.
            price = None
            try:
                from app.services.tv_price_feed import tv_feed
                # (2026-10-16، تفويض المالك) المؤشرات الأمريكية: TV يعطي المؤشر النقدي (NASDAQ:NDX/DJ:DJI/SP:SPX) —
                # بلا أسعار خارج ساعات نيويورك (NAS100 #5914 04:29 UTC لم تُرصد وبلغت وقفها) وأقل من العقد الآجل
                # بنحو 196 نقطة (NQ) بينما المستويات من get_ohlcv = العقد الآجل. فتُقاس بالعقد الآجل (smart_data
                # _FUTURES_SYMBOLS → yfinance NQ=F/YM=F/ES=F) — نفس مرجع بناء المستويات (قاعدة 16/09).
                if market_upper in TV_SYMBOL_MAP and market_upper not in _INDEX_FUTURES_REF:
                    tv_p = tv_feed.get_price_sync(market_upper)
                    if tv_p and float(tv_p) > 0:
                        price = float(tv_p)
                if price is None and market_upper in _METALS_ONLY:
                    # fallback: theoretical carry — معادن فقط، mosh_ai_engine_v5
                    # مستورد بالأعلى (سطر 15) بشكل عام؛ الاستيراد المحلي هون كان
                    # يحجبه لبقية الدالة كلها ويسبب UnboundLocalError صامت.
                    price_raw, _ = mosh_ai_engine_v5._fetch_spot_price(market_upper)
                    price = float(price_raw) if price_raw > 0 else None
                if price is None:
                    # (2026-09-16 #3) كان هنا `await` — والدالة متزامنة تُعيد
                    # dict، فيرمي await عليها TypeError يبتلعه except الحلقة
                    # فتُتخطّى الإشارة بصمت. كل مواضع الاستدعاء الأخرى
                    # بالمشروع (markets.py, main.py, ai_engine_v5, chat_agent)
                    # تستدعيها بلا await — هذان الموضعان وحدهما كانا خطأً.
                    # الأثر: الرصد التلقائي ميت لكل رمز يمرّ من هنا. كان
                    # محصوراً بالرموز خارج TradingView (ADAUSD, DOGEUSD,
                    # XPTUSD, COPPER, NATGAS, NFLX, الأسهم الخليجية) وظلّ
                    # مخفياً لأنها قليلة؛ ثم عمّ كل الرموز بتغيير اليوم.
                    price_info = _smart_data.get_realtime_price_with_meta(sig.market)
                    price = float(price_info["price"]) if price_info and price_info.get("price") else None
                if price is None and market_upper in _GULF_MAP:
                    # (2026-10-16، تفويض المالك) الأسهم الخليجية لا يعرفها yfinance/Finnhub — المسار المتزامن
                    # أعلاه يعيد None دائماً فتُتخطّى الصفقة كل دورة حتى تنتهي مدتها: 25 من 26 نتيجة فائتة
                    # بالتحقق الجماعي 16/10 كانت خليجية (16 خسارة مخفية). آخر إغلاق 1m من TradingView —
                    # نفس مصدر شموعها (get_ohlcv ← _fetch_tv_gulf_history) فالقياس بنفس مرجع بناء المستويات.
                    if market_upper not in _gulf_px_cycle:
                        _gulf_px_cycle[market_upper] = await _smart_data.get_current_price_async(market_upper)
                    price = _gulf_px_cycle[market_upper]
            except Exception as _px_err:
                logger.warning(
                    f"⚠️ تعذّر جلب السعر اللحظي لـ{market_upper} #{sig.id}: "
                    f"{type(_px_err).__name__}: {_px_err}"
                )
                price = None

            if not price:
                continue
            price  = float(price)
            entry  = float(sig.entry_price)
            sl     = float(sig.stop_loss)
            tp1    = float(sig.take_profit_1)
            tp2    = float(sig.take_profit_2)
            tp3    = float(sig.take_profit_3) if sig.take_profit_3 else None
            is_buy = sig.signal_type.value == "BUY"

            # (2026-09-09) بلاغ حقيقي: هالفحص كان يقارن السعر اللحظي بس، بينما
            # هالـendpoint نفسه ما يشتغل إلا كل 15 دقيقة (MONITOR_INTERVAL
            # بـtelegram-bot/bot.py). لو السعر لمس SL/TP لحظياً (wick) وبعدين
            # ارتد قبل الدورة الجاية، الإشارة تضل ACTIVE للأبد رغم إن أي وقف
            # خسارة حقيقي عند وسيط فعلي كان نفّذ فوراً. نجيب أعلى/أدنى سعر
            # بآخر ~30 شمعة 5m (~2.5 ساعة، يغطي أي فجوة فحص فعلياً) ونفحص
            # المدى كامل مو نقطة وحدة — بنفس أولوية SL أولاً ثم TP2 ثم TP1
            # المعتمدة أصلاً بالأسفل. get_ohlcv نفسها ترفض أي طلب bars<30
            # (شرط داخلي بالدالة)، فلازم نطلب 30 بالضبط ولو محتاجين نافذة
            # أضيق فعلياً. هذا يصلح المستقبل فقط — ما يرجّع يصحح إشارات
            # فاتها wick قبل الآن.
            # (2026-09-10) لرمز عنده Spot حي عبر TradingView: نجيب المدى من
            # نفس المصدر (fetch_tv_history، مستقل عن yfinance/finnhub) بدل
            # get_ohlcv — يحل مشكلتين مرة وحدة: (أ) دقة السعر (نفس مصدر نقطة
            # السعر فوق، بدل خلط مصدرين مختلفين قد ينحرفوا عن بعض)، و(ب)
            # تقييد معدل الطلبات — get_ohlcv عبر yfinance بيفشل بصمت لو
            # فحصنا رموز كتيرة بنفس الدورة (rate limit)، وهذا كان يفسّر
            # جزئياً ليش الرصد كان يعمل صح لرمز وحيد بس (أول رمز بالدورة
            # قبل ما نوصل لحد الطلبات) ولا يعمل للباقي.
            # (2026-09-11) بلاغ حقيقي: USDJPY وBTCUSD سُجّلوا SL_HIT خلال 1-2
            # دقيقة من إنشائهم — مستحيل طبيعياً. السبب الأول: كان يُحسب أقصى/
            # أدنى سعر لكل الشموع الـ30 (~2.5 ساعة) بدون فلترة زمنية مقابل
            # created_at، فأي لمسة تاريخية قبل وجود الإشارة كانت تُنسب لها.
            # أُصلح جزئياً (استبعاد ما قبل created_at، هامش 60ث للشمعة الجارية
            # وقت الإنشاء).
            #
            # (2026-09-12) بلاغ حقيقي ثانٍ، أعمق: حتى بعد فلترة created_at،
            # فحص تحقّق مستقل (analyze_delayed_outcome_risk.py) ع82 قراراً
            # فريداً منذ 18/8 لقى 3 حالات مؤكدة (12 مستخدم متأثر) سُجّلت
            # بعكس الحقيقة تماماً (SL_HIT مسجّل والحقيقي TP1_HIT، أو العكس).
            # السبب: max(highs)/min(lows) عبر كامل النافذة يفحص "هل السعر
            # لمس المستوى بأي وقت بالنافذة؟" بدون أي اعتبار للترتيب الزمني —
            # لو الهدف تحقق فعلياً أولاً ثم لاحقاً (بنفس النافغة الطويلة، عادة
            # بسبب فجوة فحص كبيرة) رجع السعر ولمس الستوب كمان، كان الستوب
            # يفوز دايماً لأنه مكتوب أولاً بالـif/elif — بغض النظر مين صار
            # فعلياً أولاً. الحل: نمشي شمعة-شمعة بالترتيب الزمني الصحيح
            # (الأقدم للأحدث) ونتوقف عند أول شمعة يتحقق فيها أي مستوى — نفس
            # المبدأ المستخدم أصلاً بـ_verify_signal_outcome_core (admin.py)
            # يلي أثبتنا دقته على نفس الحالات الثلاث بالضبط.
            new_status = None
            walked     = False   # هل توفّرت شموع فعلاً ومُشِيت بالترتيب الزمني؟
            has_tp2 = (tp2 > tp1) if is_buy else (tp2 < tp1)
            # (2026-09-24) خارج try/range_check عمداً — لازم تُقرأ بالفحص
            # اللحظي تحت كمان (range_check=False)، لا فقط بالمشي بالشموع.
            already_triggered = sig.entry_executed is not None
            _tp1_locked = sig.status == SignalStatus.TP1_HIT
            # (2026-10-30) TP2_HIT لا يدخل هذه الحلقة إلا صفقة تنتظر هدفها الثالث (استعلام active أعلاه)
            _tp2_locked = sig.status == SignalStatus.TP2_HIT
            if _tp1_locked or _tp2_locked:
                already_triggered = True   # هدف مسجّل ⇒ الدخول تفعّل حتماً
            _sl_after_tp1 = False          # الوقف بعد هدف مقفل (الأول أو الثاني): تبقى النتيجة وينتهي الرصد
            _tp3_hit = False
            if range_check:
                try:
                    created = sig.created_at
                    if created and created.tzinfo is None:
                        created = created.replace(tzinfo=timezone.utc)
                    created_ts = created.timestamp() - 60 if created else None

                    candles = []   # [(ts_sortable, high, low), ...] بالترتيب الزمني الصاعد
                    earliest_ts = None   # أقدم شمعة متاحة قبل الفلترة (epoch)
                    if market_upper in _SPOT_SYMBOLS:
                        raw_bars = await fetch_tv_history(TV_SYMBOL_MAP[market_upper], "5m", bars=30)
                        if raw_bars:
                            earliest_ts = min(float(b[0]) for b in raw_bars)
                            relevant = (
                                [b for b in raw_bars if float(b[0]) >= created_ts]
                                if created_ts is not None else raw_bars
                            )
                            candles = sorted(
                                ((float(b[0]), float(b[2]), float(b[3])) for b in relevant),
                                key=lambda c: c[0],
                            )
                    else:
                        range_df = await _smart_data.get_ohlcv(market_upper, "5m", bars=30)
                        if range_df is not None and len(range_df):
                            import pandas as _pd
                            # (2026-09-16) كان هنا `.values` — وهو يجرّد المنطقة
                            # الزمنية فيصير العمود tz-naive، فترمي المقارنة مع
                            # Timestamp الواعي بالمنطقة TypeError. والكتلة كلها
                            # ملفوفة بـexcept Exception فتُبتلع بصمت: candles
                            # تبقى فارغة، ويسقط الرصد للفحص بالسعر اللحظي فقط.
                            # النتيجة: المشي الزمني (إصلاح d21985f) لم يعمل
                            # إطلاقاً لأي رمز يمرّ من فرع yfinance — الكريبتو
                            # والمؤشرات والفوركس كلها. نُبقي العمود واعياً
                            # بالمنطقة بلا .values.
                            work = range_df.copy()
                            ts_col = work["datetime"] if "datetime" in work.columns else work.index
                            work["_ts"] = _pd.to_datetime(ts_col, utc=True)
                            if len(work):
                                earliest_ts = work["_ts"].min().timestamp()
                            if created_ts is not None:
                                work = work[work["_ts"] >= _pd.Timestamp(created_ts, unit="s", tz="UTC")]
                            work = work.sort_values("_ts")
                            candles = [(row["_ts"], float(row["high"]), float(row["low"])) for _, row in work.iterrows()]

                    # (2026-09-16) بلاغ حقيقي: إشارة ذهب بلغت الهدف الثاني
                    # لكنها سُجّلت "هدف أول". السبب: الحلقة كانت تتوقف عند
                    # أول لمسة أياً كانت — فإذا لُمس TP1 بشمعة مبكرة وTP2
                    # بشمعة لاحقة، تنكسر الحلقة عند TP1 ولا ترى TP2 أبداً.
                    # TP2 كان يُسجَّل فقط حين يُلمس بنفس شمعة TP1 (حركة
                    # سريعة) — أي أن الأرباح كانت تُنقَص منهجياً بالصفقات
                    # الأبطأ.
                    # الإصلاح: TP1 لم يعد نهائياً — نسجّله كأفضل نتيجة حتى
                    # الآن ونُكمل. ينتهي المسح عند SL أو TP2 فقط. ولمس SL
                    # بعد بلوغ TP1 يُبقي TP1 (الهدف الأول تحقق فعلاً
                    # وقابل للجني) — وهذا هو سلوك الكود السابق نفسه، فلا
                    # يتغيّر شيء بتلك الحالة.
                    # (2026-09-16 #2) تراجع عن `walked = bool(candles)`.
                    # كانت تعني "توفّرت شموع ⇒ حكمها نهائي"، وهي خاطئة:
                    # نافذة المشي 30 شمعة 5m = ساعتان ونصف فقط، بينما عمر
                    # الإشارة يبلغ 72 ساعة. فإشارة لمست وقفها قبل ثلاث
                    # ساعات لا تظهر لمستها بالنافذة، فيخلص المشي إلى "لم
                    # يُلمس شيء" ويُلغى الفحص اللحظي، فتبقى الإشارة ACTIVE
                    # إلى الأبد. وقد حصل فعلاً: عشرات الإشارات بقيت نشطة
                    # بينما أداة التحقق (تجلب 1000 شمعة) تؤكد أنها ضربت
                    # الوقف — فتوقّف تسجيل النتائج وتجمّدت الإحصاءات.
                    # الشرط الصحيح: يُحتكم للمشي وحده متى غطّى عمر الإشارة
                    # كاملاً، أي توفّرت شمعة عند لحظة الإنشاء أو قبلها.
                    # وإلا فالمشي رأى شريحة حديثة فقط، ويبقى الفحص اللحظي
                    # شبكة الأمان كما كان.
                    walked = bool(candles) and earliest_ts is not None and (
                        created_ts is None or earliest_ts <= created_ts
                    )
                    if candles and not walked:
                        logger.debug(
                            f"↩️ {market_upper} #{sig.id}: المشي غطّى شريحة حديثة فقط "
                            f"(أقدم شمعة بعد الإنشاء) — يبقى الفحص اللحظي فعّالاً"
                        )
                    # (2026-09-24) بوابة تفعيل الدخول: قبل هذا الإصلاح كانت
                    # الحلقة تحكم SL/TP من أول شمعة بغض النظر هل السعر لمس
                    # منطقة الدخول أصلاً — أي "أمر معلَّق" لم يتفعّل (السعر
                    # لم يصل الدخول إطلاقاً) كان يُحكَم عليه كصفقة خاسرة لو
                    # واصل بعيداً عن الدخول باتجاه الوقف. entry_executed
                    # (عمود قديم غير مُستخدَم) يُسجَّل أول لحظة يتقاطع فيها
                    # مدى الشمعة مع سعر الدخول (lo<=entry<=hi) — لا SL/TP
                    # قبلها إطلاقاً، بغض النظر عن اتجاه اقتراب السعر.
                    new_entry_ts = None
                    # (2026-10-09، بتفويض صريح) بلاغ مؤكَّد بالشموع: الدورة
                    # الأولى تتخطّى ما قبل الدخول صحيحاً، لكن بالدورات التالية
                    # already_triggered=True من entry_executed المحفوظ، فكانت
                    # الحلقة تمشي من created_at وتفحص الشموع **قبل** الدخول
                    # كأنها بعده. بيع دخل بعد أن نزل السعر من فوق الستوب كان
                    # يُسجَّل SL_HIT بشمعة سبقت فتح الصفقة — #3234 ذهب سُجّل
                    # خاسراً وسعر الإغلاق المسجّل نفسه (4192) رابح، والشموع
                    # تؤكد TP2. 5 من ~70 قراراً معادن منذ 24/09، كلها بيع بسوق
                    # هابط. والعكس ممكن (ربح وهمي من شمعة قبل الدخول).
                    # الآن: لا شمعة تسبق شمعة التفعيل تُفحص أبداً.
                    _entry_floor = None
                    _floor_src = sig.entry_executed or (sig.exit_executed if (_tp1_locked or _tp2_locked) else None)
                    if _floor_src is not None:
                        _ee = _floor_src
                        if _ee.tzinfo is None:
                            _ee = _ee.replace(tzinfo=timezone.utc)
                        _entry_floor = _ee.timestamp()
                    for _ts, hi, lo in candles:
                        if _entry_floor is not None:
                            _c_ts = _ts.timestamp() if hasattr(_ts, "timestamp") else float(_ts)
                            if _c_ts < _entry_floor:
                                continue
                        if not already_triggered:
                            if not (lo <= entry <= hi):
                                continue  # الدخول لسا ما تحقق — هذه الشمعة بلا معنى لصفقة لم تُفتح
                            already_triggered = True
                            new_entry_ts = _ts
                        sl_touch  = (lo <= sl) if is_buy else (hi >= sl)
                        tp2_touch = has_tp2 and ((hi >= tp2) if is_buy else (lo <= tp2))
                        tp1_touch = (hi >= tp1) if is_buy else (lo <= tp1)
                        if _tp2_locked:
                            # مقفول على الهدف 2: نفس منطق القفل تحت درجة أعلى — الوقف أولاً عند التعادل
                            if sl_touch:
                                _sl_after_tp1 = True
                                break
                            if (hi >= tp3) if is_buy else (lo <= tp3):
                                _tp3_hit = True
                                break
                            continue
                        if _tp1_locked:
                            # مقفول على TP1: الستوب بعده يُنهي الرصد (الهدف الأول
                            # يبقى)، وTP2 قبله يرقّي. لا شيء غيرهما.
                            if sl_touch:
                                _sl_after_tp1 = True
                                break
                            if tp2_touch:
                                new_status = SignalStatus.TP2_HIT
                                break
                            continue
                        if sl_touch:
                            new_status = new_status or SignalStatus.SL_HIT
                            break
                        if tp2_touch:
                            new_status = SignalStatus.TP2_HIT
                            break
                        if tp1_touch and new_status is None:
                            new_status = SignalStatus.TP1_HIT
                            # بلا break — نكمل لنرى هل يبلغ TP2 قبل SL

                    if new_entry_ts is not None and sig.entry_executed is None:
                        sig.entry_executed = (
                            new_entry_ts if hasattr(new_entry_ts, "tzinfo")
                            else datetime.fromtimestamp(float(new_entry_ts), tz=timezone.utc)
                        )
                        # يُحفَظ فوراً — لو ضلّت الإشارة بلا SL/TP هالدورة (فُتحت
                        # الصفقة بس ما انحسمت بعد)، ما تصير `db.commit()` تانية
                        # لهالصف قبل ما يتحدد new_status بدورة لاحقة، وبلا حفظ
                        # فوري كان ممكن يضيع مع أي rollback بنهاية الطلب.
                        db.commit()
                except Exception as _walk_err:
                    # (2026-09-16) كان `pass` صامتاً — وهو ما أخفى عطل المنطقة
                    # الزمنية أعلاه لأيام: المشي الزمني كان يرمي استثناءً بكل
                    # مرة لرموز yfinance، فيُبتلع، فيسقط الرصد للسعر اللحظي
                    # بلا أي أثر. السقوط للفحص اللحظي يبقى سلوكاً مقبولاً
                    # (أفضل من لا رصد)، لكن يجب ألا يكون صامتاً.
                    logger.warning(
                        f"⚠️ المشي الزمني فشل لـ{market_upper} #{sig.id} — "
                        f"سقوط للفحص بالسعر اللحظي: {type(_walk_err).__name__}: {_walk_err}"
                    )

            # فحص لحظي — الملاذ الأخير حين لا تتوفر شموع أصلاً.
            #
            # (2026-09-16) أُضيف شرط `not walked`. قبله كان السعر اللحظي
            # ينقض المشي الزمني كلما لم يجد الأخير لمسة: المشي يمسح كل شمعة
            # منذ الإصدار بمرجع المستويات ويخلص إلى "لم يُلمس شيء"، ثم يأتي
            # السعر اللحظي — من مسار مختلف تماماً (Finnhub/TV بينما الشموع
            # yfinance) — فيحكم SL_HIT. أي أن الحكم النهائي كان يعود للمصدر
            # الأضعف والأقل اتساقاً، ويُلغي إصلاح الترتيب الزمني (d21985f)
            # في الحالة التي وُضع لها أصلاً. فحصان بمرجعين، والأسوأ يفوز.
            # بعد الشرط: إن مُشِيت الشموع فحكمها نهائي لهذه الدورة. الفجوة
            # الوحيدة هي الشمعة الجارية غير المكتملة، وتُغطّى بالدورة
            # التالية بعد 90 ثانية.
            # (2026-09-24) لا نحكم SL/TP من تذبذبة سعرية لحظية وحيدة إلا لو
            # تأكّد تفعيل الدخول أصلاً بدورة عميقة سابقة (already_triggered).
            # سعر لحظي واحد لا يكفي لإثبات "لُمس الدخول ثم استمر" بأمان — لو
            # لسا غير مؤكَّد، ننتظر الدورة العميقة القادمة (تفحص الشموع
            # وترتيبها الزمني الصحيح) بدل تخمين قد يُخطئ بنفس الثغرة الأصلية.
            # (2026-10-10، بتفويض صريح) الفحص اللحظي للذهب والفضة فقط. السعر
            # اللحظي يُقرأ من TV لكل رمز بـTV_SYMBOL_MAP، بينما مستويات غير
            # المعادن مبنية على get_ohlcv (عقود آجلة للمؤشرات) — فخالف هذا
            # المسار قاعدة 16/09 نفسها ("تُقاس النتيجة بنفس مرجع بناء
            # المستويات"). US30 النقدي (TV) أدنى من الآجل بمئات النقاط، فبيع
            # أقدم من نافذة المشي (2.5 ساعة) كان يُحسم TP2 بسعر لم يوجد بمرجعه
            # — ~35 صفاً US30/SP500 مسجّلة TP2 والشموع تقول SL. غير المعادن
            # تُحسم بالشموع وحدها (دورة عميقة كل ~13.5 دقيقة، نافذتها 2.5 ساعة
            # فلا فجوة) — الثمن تأخّر إشعار النتيجة حتى 13.5 دقيقة.
            if _tp1_locked and new_status is None and not _sl_after_tp1 \
                    and not walked and market_upper in _SPOT_SYMBOLS:
                if (price >= tp2) if is_buy else (price <= tp2):
                    if has_tp2:
                        new_status = SignalStatus.TP2_HIT
                elif (price <= sl) if is_buy else (price >= sl):
                    _sl_after_tp1 = True

            if _tp2_locked and not _tp3_hit and not _sl_after_tp1 \
                    and not walked and market_upper in _SPOT_SYMBOLS:
                if (price >= tp3) if is_buy else (price <= tp3):
                    _tp3_hit = True
                elif (price <= sl) if is_buy else (price >= sl):
                    _sl_after_tp1 = True

            if _sl_after_tp1:
                # الصفقة أُغلقت بالستوب بعد TP1 — النتيجة تبقى TP1 وينتهي الرصد
                # (وإلا قد ترى نافذة لاحقة TP2 بعد خروج شمعة الستوب منها)
                sig.expires_at = now
                db.commit()
                continue

            if new_status is None and not walked and already_triggered \
                    and not _tp1_locked and not _tp2_locked and market_upper in _SPOT_SYMBOLS:
                if is_buy:
                    if   price <= sl:  new_status = SignalStatus.SL_HIT
                    elif price >= tp2: new_status = SignalStatus.TP2_HIT
                    elif price >= tp1: new_status = SignalStatus.TP1_HIT
                else:
                    if   price >= sl:  new_status = SignalStatus.SL_HIT
                    elif price <= tp2: new_status = SignalStatus.TP2_HIT
                    elif price <= tp1: new_status = SignalStatus.TP1_HIT

            # (2026-10-16، قرار المالك) وصلته رسالة التأمين (+1R، "انقل الوقف للدخول") ثم عاد للوقف قبل TP1 ← من
            # اتبع تعليمات المنصة خرج على الدخول: تأمين 0R لا خسارة. منذ 14/10 TP1=1R=نقطة التأمين فنادر جداً.
            if new_status == SignalStatus.SL_HIT and sig.be_alert_sent and not _tp1_locked:
                new_status = SignalStatus.BREAKEVEN

            if _tp3_hit:
                new_status = SignalStatus.TP2_HIT   # الحالة تبقى، والهدف الثالث بـtp3_hit_at (tp_ladder.py)

            if _tp3_hit or (new_status and new_status != sig.status):
                is_buy  = sig.signal_type.value == "BUY"
                points, pnl_pct, exit_p = _pnl_for_outcome(
                    entry, price, sl, tp1, tp3 if _tp3_hit else tp2, sig.market, is_buy, new_status
                )

                # حفظ النتيجة على الإشارة
                sig.status                  = new_status
                sig.current_price           = price
                sig.points_earned           = points
                sig.profit_loss             = points
                sig.profit_loss_percentage  = pnl_pct
                sig.exit_executed           = datetime.now(timezone.utc)
                if _tp3_hit:
                    sig.tp3_hit_at          = sig.exit_executed
                db.commit()

                # تحديث performance tracker في المحرك (Task 6) — مرة وحدة
                # لكل قرار فريد، مو لكل صف/مستخدم (انظر التعليق فوق الحلقة)
                dkey = decision_key(sig.market, sig.timeframe, sig.signal_type, sig.entry_price)
                # ترقية TP1→TP2 ليست قراراً جديداً — حُسب WIN عند TP1 أصلاً
                if dkey not in _perf_counted_this_cycle and not _tp1_locked and not _tp2_locked \
                        and new_status != SignalStatus.BREAKEVEN:   # التأمين ليس ربحاً ولا خسارة للمعايرة
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
                    "status":       "TP3_HIT" if _tp3_hit else new_status.value,
                    "entry":        entry,
                    "sl":           sl,
                    "tp1":          tp1,
                    "tp2":          tp2,
                    "tp3":          tp3,
                    "current_price":price,
                    "pnl_points":   points,
                    "pnl_pct":      pnl_pct,
                    "confidence":   sig.ai_confidence,
                    # (2026-10-19) لرسائل النتيجة الجديدة: "بعد X من الإشارة" وجمهور الرسالة
                    "created_at":   sig.created_at.isoformat() if sig.created_at else None,
                    "audience":     "subscriber",
                }

                # إذا كانت الإشارة مُبثّة لكل المشتركين → نُضيف كل المشتركين
                # (مرة واحدة فقط لكل قرار فريد بالدورة — راجع التعليق فوق
                # _broadcast_fanout_done_this_cycle)
                if sig.broadcast_sent:
                    if dkey not in _broadcast_fanout_done_this_cycle:
                        _broadcast_fanout_done_this_cycle.add(dkey)
                        from app.services.telegram_reach import reachable
                        active_subs = db.query(User).filter(
                            User.telegram_id != None,
                            User.is_active == True,
                            User.plan != PlanType.BANNED,
                            reachable(),   # (2026-10-19) لا إرسال لمن حظر البوت
                        ).all()
                        now_utc = datetime.now(timezone.utc)
                        for sub in active_subs:
                            valid = False
                            if sub.plan in [PlanType.WEEKLY, PlanType.MONTHLY]:
                                valid = sub.subscription_ends_at and sub.subscription_ends_at > now_utc
                            elif sub.plan == PlanType.TRIAL:
                                valid = not sub.trial_ends_at or sub.trial_ends_at > now_utc
                            if valid and sub.telegram_id:
                                triggered.append({"telegram_id": sub.telegram_id, **payload, "lang": sub.language or "ar"})
                            elif sub.telegram_id and _expired_wants_result(sub, sig.market):
                                # (2026-10-19، قرار المالك) المنتهي اشتراكه يستلم **كل** نتائج الإشارات العامة — الرابحة مفصّلة
                                # والخاسرة مختصرة (telegram-bot/messages.outcome_expired) — لتشجيعه على الاشتراك بصورة صادقة.
                                # لا يُخفى أي وقف. يحترم إيقاف الإشعارات وقائمة المراقبة.
                                triggered.append({"telegram_id": sub.telegram_id, **payload, "audience": "expired", "lang": sub.language or "ar"})
                else:
                    # إشارة خاصة بمستخدم واحد
                    user = db.query(User).filter(User.id == sig.user_id).first()
                    if user and user.telegram_id:
                        triggered.append({"telegram_id": user.telegram_id, **payload, "lang": user.language or "ar"})
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
        "min_confidence":      user.notify_min_confidence if user.notify_min_confidence is not None else 0,
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
    from app.services.telegram_reach import reachable
    users = db.query(User).filter(
        User.telegram_id != None,
        User.notifications_enabled == True,
        User.is_active == True,
        User.plan != PlanType.BANNED,
        reachable(),   # (2026-10-19) لا إرسال لمن حظر البوت
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
            "min_confidence": u.notify_min_confidence if u.notify_min_confidence is not None else 0,
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


@router.post("/mute-symbol")
def bot_mute_symbol(
    telegram_id: str = Body(..., embed=True),
    symbol: str = Body(..., embed=True),
    all_symbols: list = Body(default=[], embed=True),
    _: bool = Depends(verify_bot),
    db: Session = Depends(get_db),
):
    """(2026-10-12) زر "أوقف إشارات X" تحت الإشارة في تيليجرام.
    قائمة فارغة = كل الرموز، فالإيقاف يبدأ من كل الرموز ناقص هذا. وإن لم
    يبقَ رمز (قائمة فارغة كانت ستعني "الكل" من جديد) تُطفأ الإشعارات بدلها."""
    user = _get_linked_user(telegram_id, db)
    if not user:
        return {"ok": False, "reason": "not_linked"}
    sym = symbol.upper()
    current = [s.upper() for s in (user.notify_watchlist or [])] or [s.upper() for s in all_symbols]
    new = [s for s in current if s != sym]
    if not new:
        user.notifications_enabled = False
        db.commit()
        return {"ok": True, "all_muted": True, "remaining": 0}
    user.notify_watchlist = new
    db.commit()
    return {"ok": True, "remaining": len(new)}


@router.get("/daily-challenge")
def bot_daily_challenge(_: bool = Depends(verify_bot)):
    """(2026-10-11) سؤال تحدّي اليوم — حتمي من التاريخ (UTC)، نفسه لكل المشتركين."""
    from app.services.daily_challenge import build
    return build(datetime.now(timezone.utc).date())


@router.post("/daily-challenge/answer")
def bot_daily_challenge_answer(
    telegram_id: str = Body(..., embed=True),
    challenge_id: str = Body(..., embed=True),
    option: int = Body(..., embed=True),
    _: bool = Depends(verify_bot),
    db: Session = Depends(get_db),
):
    """يصحّح الإجابة على الخادم (من التاريخ نفسه، لا من البوت) ويضيف النقاط
    لحساب الألعاب. مرة واحدة لكل تحدٍّ لكل مستخدم؛ تحدٍّ أقدم من يومين لا يُحتسب.
    السلسلة = أيام متتالية بإجابة (صحيحة أو خاطئة) — تكافئ الرجوع اليومي،
    والنقاط للصحيحة فقط: 20 + 4 لكل يوم سلسلة حتى +20."""
    from datetime import date as _date
    from app.services.daily_challenge import build
    from app.models.game_progress import GameProgress

    try:
        day = _date.fromisoformat(challenge_id)
    except ValueError:
        return {"ok": False, "reason": "invalid"}
    today = datetime.now(timezone.utc).date()
    if not (0 <= (today - day).days <= 1):
        return {"ok": False, "reason": "expired"}

    correct = option == build(day)["correct"]
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        return {"ok": True, "correct": correct, "linked": False}

    gp = db.query(GameProgress).filter(GameProgress.user_id == user.id).first()
    if gp is None:
        gp = GameProgress(user_id=user.id, points=0, best_streak=0, week_points=0, daily_streak=0)
        db.add(gp)
    if gp.daily_last == challenge_id:
        return {"ok": True, "correct": correct, "linked": True, "already": True,
                "streak": gp.daily_streak or 0, "points": gp.points or 0}

    prev = (day - timedelta(days=1)).isoformat()
    gp.daily_streak = (gp.daily_streak or 0) + 1 if gp.daily_last == prev else 1
    gp.daily_last = challenge_id

    awarded = 0
    if correct:
        awarded = 20 + min(gp.daily_streak - 1, 5) * 4
        y, w, _w = datetime.now(timezone.utc).isocalendar()
        wk = f"{y}-W{w:02d}"
        if gp.week_key != wk:
            gp.week_key, gp.week_points = wk, 0
        gp.points = (gp.points or 0) + awarded
        gp.week_points = (gp.week_points or 0) + awarded
        blob = dict(gp.data or {})
        blob["points"] = gp.points          # الصفحة تتبنى رقم الخادم عند فتحها
        gp.data = blob
    db.commit()
    return {"ok": True, "correct": correct, "linked": True, "awarded": awarded,
            "streak": gp.daily_streak, "points": gp.points or 0}


@router.get("/breakeven-alerts")
async def bot_breakeven_alerts(
    _: bool = Depends(verify_bot),
    db: Session = Depends(get_db),
):
    """(2026-10-11) تنبيه "حرّك الستوب للدخول" لمن استلم الصفقة كاملة، حين
    تبلغ ربحاً يساوي مخاطرتها (+1R) وهي ما زالت مفتوحة.

    الدليل (diag_gold.py): 9 من خسائر الذهب و7 من الفضة بلغت +1R ثم انعكست
    للستوب؛ نقل الستوب للدخول بعد +1R حسّن الذهب −4.7R→+1.5R والفضة
    +8.0R→+9.9R على نفس الشموع.

    منفصل عمداً عن bot_check_outcomes (حلقة الرصد المجمّدة): لا يغيّر حالة
    ولا نقاطاً — الإحصاء يبقى على الستوب الأصلي. المصدر نفس قاعدة الحلقة:
    الذهب والفضة شموع TV الفورية، وغيرهما get_ohlcv (مرجع بناء المستويات).
    يُعلَّم be_alert_sent قبل الإرسال (مرة واحدة على الأكثر لكل قرار)."""
    from app.services.tv_price_feed import TV_SYMBOL_MAP, fetch_tv_history
    from app.services.decision_grouping import decision_key
    from app.models.signal_delivery import SignalDelivery

    now = datetime.now(timezone.utc)
    rows = db.query(Signal).filter(
        Signal.status == SignalStatus.ACTIVE,
        Signal.entry_executed.isnot(None),
        or_(Signal.be_alert_sent.is_(None), Signal.be_alert_sent == False),  # noqa: E712
        Signal.expires_at > now,
    ).all()

    # (2026-10-13) المعادن والطاقة فقط — diag_target_profile.py (486 قراراً، أسبوعان): نقل الوقف
    # للدخول عند 1R حسّن معادن وطاقة +16.6→+25.6R، لكنه أضرّ بالفوركس +24.1→+19.1R والكريبتو
    # +102.2→+41.9R (يقطع الصفقات التي كانت ستبلغ الهدف البعيد). قرار المالك 13/10.
    from app.models.market_config import MarketConfig
    be_markets = {r[0].upper() for r in db.query(MarketConfig.symbol)
                  .filter(MarketConfig.category == "commodity").all()}
    rows = [s for s in rows if (s.market or "").upper() in be_markets]

    groups: dict = {}
    for s in rows:
        groups.setdefault(decision_key(s.market, s.timeframe, s.signal_type, s.entry_price), []).append(s)

    candle_cache: dict = {}

    async def _candles(market: str):
        """[(epoch, high, low), ...] لآخر ~5 ساعات من شموع 5m، بمرجع المستويات."""
        if market in candle_cache:
            return candle_cache[market]
        out = []
        try:
            if market in ("XAUUSD", "XAGUSD") and market in TV_SYMBOL_MAP:
                bars = await fetch_tv_history(TV_SYMBOL_MAP[market], "5m", bars=60)
                out = [(float(b[0]), float(b[2]), float(b[3])) for b in (bars or [])]
            else:
                df = await _smart_data.get_ohlcv(market, "5m", bars=60)
                if df is not None and len(df):
                    import pandas as _pd
                    ts = _pd.to_datetime(df["datetime"] if "datetime" in df.columns else df.index, utc=True)
                    out = [(t.timestamp(), float(h), float(l)) for t, h, l in zip(ts, df["high"], df["low"])]
        except Exception as _ce:
            logger.warning(f"breakeven-alerts candles {market}: {_ce}")
        candle_cache[market] = out
        return out

    alerts = []
    for _dkey, grp in groups.items():
        rep = grp[0]
        market = rep.market.upper()
        if not _smart_data.is_market_open(rep.market):
            continue
        entry, sl = float(rep.entry_price), float(rep.stop_loss)
        risk = abs(entry - sl)
        if not risk:
            continue
        is_buy = rep.signal_type.value == "BUY"
        ee = rep.entry_executed if rep.entry_executed.tzinfo else rep.entry_executed.replace(tzinfo=timezone.utc)
        floor = ee.timestamp()

        best = 0.0
        stopped = False
        for ts, hi, lo in await _candles(market):
            if ts < floor:
                continue
            if (lo <= sl) if is_buy else (hi >= sl):
                stopped = True          # الحلقة ستحسمها خسارة — لا تنبيه
                break
            best = max(best, ((hi - entry) if is_buy else (entry - lo)) / risk)
        if stopped or best < 1.0:
            continue

        # المستلمون: من استلم النسخة الكاملة فعلاً + صاحب صف المراقبة الشخصية
        row_ids = [r.id for r in grp]
        tids = {t for (t,) in db.query(SignalDelivery.telegram_id).filter(
            SignalDelivery.signal_id.in_(row_ids),
            SignalDelivery.ok == True,       # noqa: E712
            SignalDelivery.variant == "full",
        ).all() if t}
        owners = db.query(User).filter(User.id.in_({r.user_id for r in grp if r.user_id})).all()
        tids |= {str(u.telegram_id) for u in owners if u.telegram_id}

        for r in grp:
            r.be_alert_sent = True
        db.commit()

        for tid in tids:
            alerts.append({
                "telegram_id": tid,
                "signal_id":   rep.id,
                "market":      rep.market,
                "timeframe":   rep.timeframe,
                "signal_type": rep.signal_type.value,
                "entry":       entry,
                "sl":          sl,
                "tp1":         float(rep.take_profit_1),
                "tp2":         float(rep.take_profit_2) if rep.take_profit_2 else None,
            })
        logger.info(f"🛡️ breakeven alert {market} #{rep.id} +{best:.2f}R → {len(tids)} مستلم")

    return {"alerts": alerts, "count": len(alerts)}


_SAME_TRADE_ENTRY_TOL = 0.0005   # 0.05% — نفس عتبة diag_duplicates.py


def _entries_equivalent(a, b) -> bool:
    try:
        a, b = float(a), float(b)
        return a > 0 and abs(a - b) / a <= _SAME_TRADE_ENTRY_TOL
    except (TypeError, ValueError):
        return False


def _equivalent_open_broadcast(db: Session, s: Signal) -> bool:
    """هل بُثّت للمشتركين صفقة مكافئة (نفس الرمز والاتجاه، دخول ضمن 0.05%،
    أي فريم) وما زالت مفتوحة (ACTIVE أو TP1_HIT ضمن مدتها)؟"""
    now = datetime.now(timezone.utc)
    others = db.query(Signal).filter(
        Signal.market == s.market,
        Signal.signal_type == s.signal_type,
        Signal.broadcast_sent == True,  # noqa: E712
        Signal.id != s.id,
        or_(Signal.status.in_([SignalStatus.ACTIVE, SignalStatus.TP1_HIT]), tp3_open_clause(Signal)),
        Signal.expires_at > now,
    ).all()
    return any(_entries_equivalent(o.entry_price, s.entry_price) for o in others)


def _open_equivalent_rows(db: Session, market: str, signal_type, entry, exclude_id: Optional[int] = None) -> list:
    """كل الصفوف المفتوحة لنفس الصفقة: نفس الرمز والاتجاه، دخول ضمن 0.05%، أي فريم،
    ACTIVE أو TP1_HIT ولم تنتهِ مدتها."""
    now = datetime.now(timezone.utc)
    q = db.query(Signal).filter(
        Signal.market == market,
        Signal.signal_type == signal_type,
        or_(Signal.status.in_([SignalStatus.ACTIVE, SignalStatus.TP1_HIT]), tp3_open_clause(Signal)),
        (Signal.expires_at.is_(None)) | (Signal.expires_at > now),
    )
    if exclude_id is not None:
        q = q.filter(Signal.id != exclude_id)
    return [o for o in q.all() if _entries_equivalent(o.entry_price, entry)]


def _user_already_has_trade(db: Session, user: User, market: str, signal_type, entry, sl=None, tp1=None) -> bool:
    """(2026-10-12) هل وصلت هذا المستخدم الصفقة نفسها وما زالت مفتوحة — بالبث العام
    (SignalDelivery ناجح) أو بمراقبته الشخصية على فريم آخر؟ تقرير 12/10: SOL/ADA/BNB
    صدرت بالبث ثم بعد 13-31 دقيقة "تنبيه مراقبة" لنفس الدخول لـ7-12 مشتركاً، لأن
    _user_has_active_signal يفحص صفوف المستخدم على نفس الفريم فقط = مخاطرة مضاعفة."""
    from app.models.signal_delivery import SignalDelivery
    rows = _open_equivalent_rows(db, market, signal_type, entry)
    if sl is not None and tp1 is not None:
        # (2026-10-15) XRPUSD 15/10: البث 09:05 دخول 1.3170 ثم مراقبة 9 مشتركين 09:15 دخول 1.3182 (+0.09%) بنفس
        # الوقف حرفياً — نفس الإعداد أُعيد اكتشافه بسعر اللحظة فوصلهم مرتين. نفس الوقف والهدف = نفس الصفقة.
        from app.services.decision_grouping import _same_trade_wide
        now = datetime.now(timezone.utc)
        new = {"entry_price": entry, "stop_loss": sl, "take_profit_1": tp1}
        seen = {r.id for r in rows}
        rows += [o for o in db.query(Signal).filter(
                    Signal.market == market, Signal.signal_type == signal_type,
                    or_(Signal.status.in_([SignalStatus.ACTIVE, SignalStatus.TP1_HIT]), tp3_open_clause(Signal)),
                    (Signal.expires_at.is_(None)) | (Signal.expires_at > now)).all()
                 if o.id not in seen and _same_trade_wide(
                     {"entry_price": o.entry_price, "stop_loss": o.stop_loss, "take_profit_1": o.take_profit_1}, new)]
    if not rows:
        return False
    if any(r.user_id == user.id for r in rows):
        return True
    ids = [r.id for r in rows]
    who = [SignalDelivery.user_id == user.id]
    if user.telegram_id:
        who.append(SignalDelivery.telegram_id == str(user.telegram_id))
    return db.query(SignalDelivery.id).filter(
        SignalDelivery.signal_id.in_(ids),
        SignalDelivery.ok == True,  # noqa: E712
        or_(*who),
    ).first() is not None


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

        # (2026-10-10) لا تبث نفس الصفقة مرتين. diag_duplicates.py: 118 زوجاً
        # خلال 14 يوماً بُثّ كلاهما لكل المشتركين — نفس الرمز والاتجاه ودخول
        # شبه مطابق، والأولى لسا مفتوحة. مصادرها: نفس المستويات على فريم آخر
        # (15m و1h)، أو صف مراقبة شخصية لمشترك ثم مسح عام لنفس الإعداد بعد
        # دقائق. فحص الدفعة تحت كان يقارن (رمز+فريم+اتجاه) داخل الدفعة فقط.
        # إعادة الدخول بنفس المستوى **بعد** إغلاق الأولى صفقة جديدة — تُبث.
        if _equivalent_open_broadcast(db, s):
            s.broadcast_sent = True
            db.commit()
            logger.info(f"⏭️  Signal #{s.id} [{s.market}/{s.timeframe}] skipped — نفس صفقة مفتوحة بُثّت سابقاً")
            continue

        # (2026-08-31) إشارات المراقبة الشخصية (save-alert-signal) محفوظة
        # بـuser_id المستخدم الحقيقي، وبتوصله أصلاً كـ"تنبيه مراقبة" منفصل
        # (monitor_watchlists). نجيب تلغرام آيدي صاحبها هون عشان نستثنيه من
        # هالبث العام لنفس الإشارة — تجنّباً لتكرار نفس الفرصة عليه مرتين.
        owner_tid = None
        if s.user_id:
            owner = db.query(User.telegram_id).filter(User.id == s.user_id).first()
            owner_tid = owner[0] if owner else None
        # (2026-10-12) owner_tid يستثني صاحب صف واحد فقط — لكن نفس الإعداد يُنشأ صفاً
        # شخصياً لكل مشترك يراقب الرمز. نستثني كل من عنده صف مفتوح لنفس الصفقة.
        owner_uids = {r.user_id for r in _open_equivalent_rows(db, s.market, s.signal_type, s.entry_price)
                      if r.user_id} | ({s.user_id} if s.user_id else set())
        owner_tids = [str(t) for (t,) in db.query(User.telegram_id).filter(
            User.id.in_(owner_uids), User.telegram_id.isnot(None)).all()] if owner_uids else []

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
            "take_profit_3":  s.take_profit_3,
            "risk_reward_ratio": s.risk_reward_ratio,
            "wyckoff_phase":  s.wyckoff_phase,
            "premium_discount": s.premium_discount,
            "news_context":   s.notes,
            "owner_telegram_id": owner_tid,
            "owner_telegram_ids": owner_tids,
            "expires_at":     s.expires_at.isoformat() if s.expires_at else None,
        })

    # إزالة التكرار داخل الدفعة: إشارة واحدة لكل (رمز + إطار + اتجاه)، و(2026-10-10)
    # لكل (رمز + اتجاه + دخول شبه مطابق) عبر الفريمات — نفس الصفقة على 15m و1h
    # بنفس الدفعة كانت تمرّ مرتين.
    seen: set = set()
    deduped = []
    for sig in result:
        key = (sig["market"], sig["timeframe"], sig["signal_type"])
        same_trade = any(
            d["market"] == sig["market"] and d["signal_type"] == sig["signal_type"]
            and _entries_equivalent(d["entry_price"], sig["entry_price"])
            for d in deduped
        )
        if key not in seen and not same_trade:
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


@router.post("/record-deliveries/{signal_id}")
def bot_record_deliveries(
    signal_id: int,
    deliveries: list = Body(..., embed=True),
    _: bool = Depends(verify_bot),
    db: Session = Depends(get_db),
):
    """
    (2026-09-16) يسجّل من استلم الإشارة فعلاً ومتى — دفعة واحدة لكل
    إشارة، لا طلب لكل مستلم (البث يصل ~60 مشتركاً، فالطلب المنفرد كان
    سيعني 60 رحلة شبكة لكل إشارة).

    قبل هذا لم يكن هناك أي سجل: الحلقة ترسل ثم تزيد عدّاداً محلياً
    وتعلّم broadcast_sent=True فقط. فعمود "المستخدمون" بلوحة الإدارة
    كان يعدّ صفوف Signal (من أُنشئت لحسابه) لا المستلمين.

    كل عنصر: {telegram_id, ok, variant, error}
    """
    from app.models.signal_delivery import SignalDelivery

    sig = db.query(Signal).filter(Signal.id == signal_id).first()
    if not sig:
        raise HTTPException(404, "Signal not found")

    tids = [str(d.get("telegram_id")) for d in deliveries if d.get("telegram_id")]
    users = {}
    if tids:
        for u in db.query(User).filter(User.telegram_id.in_(tids)).all():
            users[str(u.telegram_id)] = u.id

    saved = 0
    for d in deliveries:
        tid = str(d.get("telegram_id") or "") or None
        if not tid:
            continue
        db.add(SignalDelivery(
            signal_id   = signal_id,
            user_id     = users.get(tid),
            telegram_id = tid,
            variant     = str(d.get("variant") or "full")[:20],
            ok          = bool(d.get("ok", True)),
            error       = (str(d.get("error"))[:300] if d.get("error") else None),
        ))
        saved += 1
    # (2026-10-19) من رد تيليجرام "محظور" يُستبعد من البث القادم؛ ومن وصله إرسال تُمسح علامته
    from app.services.telegram_reach import apply_results
    reach = apply_results(db, [(d.get("telegram_id"), bool(d.get("ok", True)), d.get("error")) for d in deliveries])
    db.commit()
    return {"success": True, "saved": saved, **reach}


@router.post("/telegram-seen")
def bot_telegram_seen(
    telegram_id: str = Body(..., embed=True),
    _: bool = Depends(verify_bot),
    db: Session = Depends(get_db),
):
    """(2026-10-19) المستخدم تفاعل مع البوت (/start، زر، رسالة) ← فكّ الحظر، يرجع لقوائم الإرسال فوراً."""
    from app.services.telegram_reach import mark_seen
    return {"unblocked": mark_seen(db, telegram_id)}


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
    """أدمن أو اشتراك مدفوع **فعّال** — (2026-10-25) من services/signal_quota.tier_of (مصدر واحد مع الموقع)."""
    from app.services.signal_quota import has_full_access
    return has_full_access(u)


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
    from app.services.telegram_reach import reachable
    users = db.query(User).filter(
        User.telegram_id != None,
        User.is_active == True,
        User.plan != PlanType.BANNED,
        reachable(),   # (2026-10-19) لا إرسال لمن حظر البوت — telegram_reach.py
    ).all()

    # (2026-10-12) تفضيلات كل مشترك مع القائمة نفسها — مصدر واحد للبث. قبلها
    # كان البوت يأخذ فلتر الأزواج من /all-watchlists التي تستبعد من أطفأ
    # الإشعارات ومن لم يؤكّد بريده، فيعاملهم البث كأنهم "بلا تخصيص" ويرسل لهم
    # **كل** الإشارات — عكس اختيارهم تماماً.
    result = [
        {
            "telegram_id":           u.telegram_id,
            "full_access":           _bot_has_full_signal_access(u),
            "notifications_enabled": u.notifications_enabled is not False,
            "watchlist":             [s.upper() for s in (u.notify_watchlist or [])],
            "timeframes":            list(u.notify_timeframes or []),
            "min_confidence":        u.notify_min_confidence if u.notify_min_confidence is not None else 0,
            "lang":                  u.language or "ar",   # (2026-10-24) رسائل البوت بلغة حساب المستخدم
        }
        for u in users
    ]

    return {"subscribers": result, "count": len(result)}


@router.post("/consume-signal-notification")
def bot_consume_signal_notification(
    telegram_id: str = Body(..., embed=True),
    signal_id: Optional[int] = Body(None, embed=True),
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

    # (2026-10-25) حد فئة المستخدم: تجربة نشطة (افتراضي بلا حد) أو منتهية — signal_quota.limit_for
    from app.services.signal_quota import limit_for
    free_limit = limit_for(db, user)
    if free_limit <= 0:
        return {"unlocked": True}

    # (2026-10-19، قرار المالك "وحّد") حصة واحدة مع الموقع (signal_quota): الإشارة تُسجَّل باسمه فتبقى مفتوحة بالموقع
    # حتى نهاية اليوم، وما فتحه بالموقع لا يُحسب مرة ثانية هنا. العدّاد القديم أدناه احتياط لطلب بلا signal_id فقط.
    sig = db.query(Signal).filter(Signal.id == signal_id).first() if signal_id else None
    if sig is not None:
        from app.services.signal_quota import try_unlock
        return {"unlocked": try_unlock(db, user.id, sig, "telegram", limit=free_limit)}

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


@router.get("/latest-signals")
async def bot_latest_signals(
    telegram_id: str,
    limit: int = 8,
    _: bool = Depends(verify_bot),
    db: Session = Depends(get_db),
):
    """(2026-10-19) زر "آخر الإشارات" بالبوت — كان يستدعي /signals/latest بمفتاح البوت، والمسار يطلب توكن مستخدم،
    فيرجع 401 دائماً ويعرض "لا توجد إشارات" للجميع. الآن: نفس دالة الموقع باسم المستخدم المرتبط، فيرى بالضبط ما يراه
    بالداشبورد (كاملة للمشترك، أول N كاملة للتجربة والباقي مموّه بلا اتجاه)."""
    from app.api.signals import get_latest_signals

    user = _get_linked_user(telegram_id, db)
    if not user:
        return {"linked": False, "data": []}
    res = await get_latest_signals(limit=max(1, min(limit, 20)), hours=12, user=user, db=db)
    return {**res, "linked": True}


@router.get("/user-lang")
def bot_user_lang(telegram_id: str, _: bool = Depends(verify_bot), db: Session = Depends(get_db)):
    """(2026-10-24) لغة حساب المستخدم المرتبط — البوت يسألها عند أول تفاعل (ensure_lang) بدل انتظار بث يملأ ذاكرته."""
    user = _get_linked_user(telegram_id, db)
    return {"lang": (user.language or "ar")} if user else {}


@router.get("/review-status")
def bot_review_status(
    telegram_id: str,
    _: bool = Depends(verify_bot),
    db: Session = Depends(get_db),
):
    """(2026-10-24) هل يحق للمستخدم المرتبط إرسال رأي من البوت؟ (نفس شرط الموقع: مشترك مدفوع ≥7 أيام)."""
    from app.api.reviews import _eligibility
    from app.models.review import Review
    user = _get_linked_user(telegram_id, db)
    if not user:
        return {"linked": False}
    el = _eligibility(db, user)
    r = db.query(Review).filter(Review.user_id == user.id).first()
    return {"linked": True, "eligible": el["eligible"], "reason": el["reason"], "days_left": el["days_left"],
            "existing": r.status if r else None}


@router.post("/reviews")
def bot_submit_review(
    telegram_id: str = Body(..., embed=True),
    rating: int = Body(..., embed=True),
    text: str = Body(..., embed=True),
    media_type: Optional[str] = Body(None, embed=True),
    media_file_id: Optional[str] = Body(None, embed=True),
    anonymous: bool = Body(False, embed=True),
    consent: bool = Body(False, embed=True),
    _: bool = Depends(verify_bot),
    db: Session = Depends(get_db),
):
    """(2026-10-24) رأي من البوت بنص وصورة/فيديو — يذهب لمراجعة الأدمن؛ عند الاعتماد يُنشر بالقناة (admin.py)."""
    from app.api.reviews import upsert_bot_review
    user = _get_linked_user(telegram_id, db)
    if not user:
        return {"ok": False, "error": "اربط حسابك أولاً"}
    return upsert_bot_review(db, user, rating, text, media_type, media_file_id, anonymous, consent)


@router.get("/user-stats")
def bot_user_stats(
    telegram_id: str,
    _: bool = Depends(verify_bot),
    db: Session = Depends(get_db),
):
    """إحصائيات المستخدم للبوت

    (2026-10-03) صارت تستدعي get_user_lifetime_stats (signals.py) —
    نفس الدالة المستخدَمة بإحصائيات الداشبورد، بدل فلترة منفصلة كانت
    تعتمد على Signal.user_id (صفوف مملوكة تاريخياً) لا notify_watchlist
    الحالي ولا data_floor. راجع تعليق تلك الدالة للتفصيل الكامل — ضَمِن
    هذا تطابق أرقام البوت مع الداشبورد تماماً لنفس المستخدم بنفس اللحظة."""
    from app.api.signals import get_user_lifetime_stats

    user = _get_linked_user(telegram_id, db)
    if not user:
        return {"linked": False}

    stats = get_user_lifetime_stats(db, user)
    total  = stats["total"]
    wins   = stats["wins"]
    pts    = stats["total_points"]
    best   = stats["best_trade"]
    worst  = stats["worst_trade"]
    active = stats["active_signals"]

    recent = []
    for r in stats["recent_trades"]:
        icon = "✅" if r["status"] in ("TP1_HIT", "TP2_HIT") else "❌"
        recent.append({**r, "icon": icon})

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
        "losses":         stats["losses"],
        "win_rate":       stats["win_rate"],
        "total_points":   round(float(pts), 2),
        "active_signals": active,
        "best_trade":     round(float(best), 2),
        "worst_trade":    round(float(worst), 2),
        "recent_trades":  recent,
        "watchlist_filter":  stats["watchlist_filter"],
        # (2026-10-19) بطاقة البوت الجديدة بـR (telegram-bot/messages.stats_card)
        "plan":           str(user.plan.value if hasattr(user.plan, "value") else user.plan).lower(),
        "lang":           user.language or "ar",
        "total_r":        stats["total_r"],
        "avg_r":          stats["avg_r"],
        "best_r":         stats["best_r"],
        "worst_r":        stats["worst_r"],
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
    tp3: Optional[float] = None,              # (2026-10-30) سلّم الأهداف — tp_ladder.py
    wyckoff_phase: Optional[str] = None,      # (2026-10-16) سياق ICT — كان يُحفظ بمسار الماسح فقط
    premium_discount: Optional[str] = None,
    killzone: Optional[str] = None,
    relaxed_rule: Optional[str] = None,       # (2026-10-24) من analysis["relaxed_rule"] — relax_policy.py
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

    # (2026-10-24) صفقة مخفَّفة تتعارض مع صفقة منصة نشطة بعكسها — لا تنبيه متضاد
    if should_drop_relaxed(db, {"relaxed_rule": relaxed_rule, "recommendation": signal_type}, symbol):
        return {"saved": False, "reason": "relaxed_conflict"}

    if _user_already_has_trade(db, user, symbol, ST(signal_type), entry, sl, tp1):
        return {"saved": False, "reason": "same open trade already delivered to this user"}

    tf_hours   = {"1m": 2, "5m": 4, "15m": 3, "30m": 12, "1h": 24, "4h": 72, "1d": 168}

    # (2026-10-12) كريبتو بالعطلة → لا تنبيه مراقبة؛ يُحفظ بجدول الظل للقياس فقط
    from app.services.weekend_policy import crypto_weekend_paused, record_shadow
    if crypto_weekend_paused(db, symbol):
        record_shadow(db, source="watch", symbol=symbol, timeframe=timeframe, signal_type=signal_type,
                      entry=entry, sl=sl, tp1=tp1, tp2=tp3 or tp2, confidence=confidence, rr=rr,
                      expires_at=datetime.now(timezone.utc) + timedelta(hours=tf_hours.get(timeframe, 24)),
                      user_id=user.id)
        return {"saved": False, "reason": "crypto_weekend_pause"}

    # (2026-10-03) 15m كانت 8 ساعات (32× حجم الشمعة — شذوذ مقارنة بالجدول
    # المتدرّج حولها: 5m=48×، 30m=24×). بنية السوق يلي بُنيت عليها إشارة
    # 15m تتغيّر فعلياً خلال ساعات قليلة، فـ8 ساعات تعني إشارة "صالحة"
    # لإعداد عملياً انتهى بحكم الواقع. نزلت لـ3 ساعات (12× — أقرب لانحدار
    # الجدول). بتفويض صريح من صاحب المنتج. (tf_hours معرّف أعلاه — قبل فحص الكريبتو)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=tf_hours.get(timeframe, 24))

    sig_hash = hashlib.md5(
        f"{user.id}-{symbol}-{timeframe}-{signal_type}-{entry:.5f}".encode()
    ).hexdigest()

    existing = db.query(Signal).filter(Signal.signal_hash == sig_hash).first()
    if existing:
        return {"saved": False, "reason": "duplicate", "signal_id": existing.id}

    sig = Signal(
        relaxed_rule      = relaxed_rule if relaxed_rule == "SELL_IN_DISCOUNT" else None,
        user_id           = user.id,
        market            = symbol,
        timeframe         = timeframe,
        signal_type       = ST(signal_type),
        signal_quality    = SignalQuality.PREMIUM if confidence >= 80 else SignalQuality.STANDARD,
        status            = SignalStatus.ACTIVE,
        wyckoff_phase     = wyckoff_phase or None,
        premium_discount  = premium_discount or None,
        killzone          = killzone or None,
        entry_price       = round(entry, 5),
        stop_loss         = round(sl, 5),
        take_profit_1     = round(tp1, 5),
        take_profit_2     = round(tp2, 5),
        take_profit_3     = round(tp3, 5) if tp3 else None,
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

    # (2026-09-27) استطلاع الميزات: "تحذير عند أكثر من صفقة مرتبطة مفتوحة
    # بنفس الوقت" (10 أصوات، أعلى طلب مع عداد الانتهاء). التعريف المعتمد:
    # نفس الرمز فقط (بغض النظر عن الفريم/الاتجاه) — بلاغ حقيقي سابق (فضة
    # شراء + بيع مفتوحتين معاً) كان بالضبط هالحالة.
    concurrent_same_symbol = db.query(Signal).filter(
        Signal.user_id == user.id,
        Signal.market == symbol,
        Signal.status == SignalStatus.ACTIVE,
        Signal.id != sig.id,
    ).count()
    return {"saved": True, "signal_id": sig.id, "concurrent_same_symbol": concurrent_same_symbol}


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
