"""
Mosh AI Pro v5 - Signals API Routes
"""

import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from loguru import logger

from app.database import get_db
from app.services.ai_engine_v5 import mosh_ai_engine_v5
from app.models import Signal, AnalysisLog
from app.models.signal import Signal, SignalType, SignalStatus, SignalQuality
from app.models.user import User, PlanType, UserRole
from app.models.site_settings import SiteSettings
from app.services.auth_service import get_current_user, check_subscription, deduct_trial
from app.api.bot import _check_loss_streak_breaker, _has_active_signal


def _calc_lot_size(account_balance: float, risk_percent: float,
                   entry: float, sl: float, symbol: str) -> float | None:
    """
    حساب حجم اللوت المناسب بناءً على رأس المال والمخاطرة.
    pip_value: تقريبي — $10 لكل 0.01 لوت لمعظم أزواج الفوركس
    """
    try:
        if not entry or not sl or entry == sl:
            return None
        risk_amount = account_balance * (risk_percent / 100)
        sl_pips = abs(entry - sl)
        if sl_pips == 0:
            return None
        # تحديد قيمة النقطة حسب الزوج
        if symbol in ("XAUUSD",):
            pip_value_per_lot = 10.0     # $10 لكل نقطة لكل لوت قياسي
        elif symbol in ("BTCUSD",):
            pip_value_per_lot = 1.0
        elif symbol in ("USDJPY", "USDCHF"):
            pip_value_per_lot = 8.0
        else:
            pip_value_per_lot = 10.0     # افتراضي للفوركس
        lot = risk_amount / (sl_pips * pip_value_per_lot)
        return round(max(0.01, min(lot, 100.0)), 2)
    except Exception:
        return None

router = APIRouter()


def _trial_signal_daily_limit(db: Session) -> int:
    """عدد الإشارات الكاملة (غير مموّهة) المسموحة يومياً لمستخدمي التجربة —
    قابل للتعديل من لوحة الإدارة (SiteSettings)، مطابق لنمط trial_analysis_limit."""
    row = db.query(SiteSettings).filter(SiteSettings.key == "trial_signal_daily_limit").first()
    try:
        return int(row.value) if row and row.value else 3
    except Exception:
        return 3


def _has_full_signal_access(user: Optional[User]) -> bool:
    """أدمن أو مشترك فعلي (أسبوعي/شهري) يشوف كل تفاصيل كل الإشارات دايماً،
    بدون حد يومي ولا تمويه."""
    if not user:
        return False
    if user.role == UserRole.ADMIN:
        return True
    return user.plan in (PlanType.WEEKLY, PlanType.MONTHLY)


@router.post("/analyze")
async def analyze_market(
    symbol: str,
    timeframe: str = "1h",
    advanced_mode: bool = True,
    force_refresh: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """تحليل السوق مع فحص الصلاحية وكاش ذكي"""
    status = check_subscription(user, db)
    if not status["allowed"]:
        raise HTTPException(status_code=403, detail=status["reason"])

    if user.plan == PlanType.TRIAL and user.trial_analyses_left <= 0:
        raise HTTPException(
            status_code=403,
            detail="استهلكت تحليلات التجربة المجانية. اشترك للمتابعة."
        )

    try:
        # من الكاش؟ لا نخصم كريدت
        analysis = await mosh_ai_engine_v5.analyze_market(
            symbol=symbol,
            timeframe=timeframe,
            advanced_mode=advanced_mode,
            force_refresh=force_refresh,
            account_balance=float(getattr(user, "account_balance", 10000.0) or 10000.0),
            max_risk_percent=float(getattr(user, "risk_percent", 1.5) or 1.5),
        )

        # نخصم كريدت فقط إذا كان تحليلاً جديداً (مش من الكاش)
        if not analysis.get("from_cache", False):
            if user.plan == PlanType.TRIAL:
                deduct_trial(user, db, kind="analysis")
            else:
                user.analyses_total     += 1
                user.analyses_used_today += 1
                db.commit()


        # استخراج المستويات (safe — entry_zones / take_profit_zones قد تكون فارغة)
        rec    = analysis.get("recommendation", "WAIT")
        levels = analysis.get("levels", {})
        _ez    = analysis.get("entry_zones") or []
        _tz    = analysis.get("take_profit_zones") or []
        entry  = levels.get("entry") or (_ez[0] if _ez else None)
        sl     = levels.get("stop_loss") or analysis.get("stop_loss_zone")
        tp1    = levels.get("tp1") or (_tz[0] if _tz else None)
        tp2    = levels.get("tp2") or (_tz[1] if len(_tz) > 1 else None)
        conf   = analysis.get("ai_confidence_score", 0)
        rr     = levels.get("risk_reward")

        # حساب اللوت المناسب
        bal    = float(getattr(user, "account_balance", 10000.0) or 10000.0)
        risk   = float(getattr(user, "risk_percent", 1.5) or 1.5)
        lot    = _calc_lot_size(bal, risk, entry or 0, sl or 0, symbol) if entry and sl else None
        if lot:
            analysis["lot_size"]       = lot
            analysis["account_balance"] = bal
            analysis["risk_percent"]   = risk

        # حفظ سجل التحليل (كل تحليل)
        try:
            log = AnalysisLog(
                user_id       = user.id,
                market        = symbol,
                timeframe     = timeframe,
                recommendation= rec,
                confidence    = conf,
                current_price = analysis.get("current_price"),
                entry         = float(entry) if entry else None,
                sl            = float(sl)    if sl    else None,
                tp1           = float(tp1)   if tp1   else None,
                tp2           = float(tp2)   if tp2   else None,
                rr            = float(rr)    if rr    else None,
                lot_size      = lot,
                from_cache    = analysis.get("from_cache", False),
                full_result   = {k: v for k, v in analysis.items()
                                 if k not in ("from_cache",) and not isinstance(v, (bytes,))},
            )
            db.add(log)
            db.commit()
        except Exception as _le:
            logger.warning(f"AnalysisLog save error: {_le}")

        # حفظ الإشارة — شروط صارمة + Cooldown
        from app.services.smart_data import smart_data as _sd
        try:
            _rr_ok  = rr and float(rr) >= 1.2
            _rej    = (analysis.get("validation_rejected") or
                       analysis.get("sweep_gate_blocked") or
                       analysis.get("price_gap_rejected"))

            # ── Cooldown check (Task 5) ────────────────────────────────────
            _cooldown_ok = mosh_ai_engine_v5.check_cooldown(symbol, timeframe)

            if rec in ("BUY", "SELL") and entry and sl and tp1 \
                    and conf >= 40 and _rr_ok and not _rej and _cooldown_ok \
                    and analysis.get("market_open", True) and _sd.is_market_open(symbol):

                sig_type  = SignalType.BUY if rec == "BUY" else SignalType.SELL
                tf_hours  = {"1m":2,"5m":4,"15m":8,"30m":12,"1h":24,"4h":72,"1d":168,"1w":336}
                expires_h = tf_hours.get(timeframe, 24)
                expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_h)
                # hash لا يشمل user_id — إشارة واحدة لكل (رمز+إطار+اتجاه+entry) في الكل
                sig_hash = hashlib.md5(
                    f"{symbol}-{timeframe}-{rec}-{round(float(entry), 4)}".encode()
                ).hexdigest()
                existing   = db.query(Signal).filter(Signal.signal_hash == sig_hash).first()
                active_dup = _has_active_signal(db, symbol, timeframe)

                # ── Loss-streak breaker (2026-08-18) ─────────────────────────
                # كان مربوطاً فقط بمسارات bot.py (bot_analyze / save-alert-signal)
                # — هاد المسار (تحليل من الموقع مباشرة) كان يتجاوزه بالكامل،
                # وهو الأعلى حجماً لرمز شعبي زي XAUUSD. نفس الدالة والمنطق تماماً.
                loss_streak_reason = _check_loss_streak_breaker(db, symbol, rec)
                if loss_streak_reason:
                    analysis["loss_streak_blocked"] = True
                    analysis["rejection_reason"]    = loss_streak_reason.upper()
                    logger.warning(
                        f"⛔ Signal save blocked by loss-streak breaker: "
                        f"{symbol}/{timeframe} {rec} — {loss_streak_reason}"
                    )
                elif not existing and not active_dup:
                    new_sig = Signal(
                        user_id           = user.id,
                        market            = symbol,
                        timeframe         = timeframe,
                        signal_type       = sig_type,
                        signal_quality    = SignalQuality.PREMIUM if conf >= 80 else SignalQuality.STANDARD,
                        status            = SignalStatus.ACTIVE,
                        entry_price       = float(entry),
                        stop_loss         = float(sl),
                        take_profit_1     = float(tp1),
                        take_profit_2     = float(tp2 or tp1),
                        current_price     = analysis.get("current_price"),
                        ai_confidence     = conf,
                        risk_reward_ratio = rr,
                        signal_hash       = sig_hash,
                        expires_at        = expires_at,
                    )
                    db.add(new_sig)
                    db.commit()
                    # سجّل الـ cooldown بعد الحفظ
                    mosh_ai_engine_v5.record_signal_sent(symbol, timeframe)
                    logger.info(
                        f"Signal saved: {symbol}/{timeframe} {rec} "
                        f"entry={entry} rr={rr} conf={conf}%"
                    )
        except Exception as _se:
            logger.warning(f"Signal save error: {_se}")

        return {"success": True, "data": analysis}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in analysis endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest_signals(
    limit: int = 10,
    hours: int = 12,   # only return signals created within this window
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get latest ACTIVE/PENDING signals within the last `hours` window.

    الوصول الكامل (كل التفاصيل) للأدمن والمشتركين (أسبوعي/شهري) فقط —
    مستخدم التجربة يشوف أول N إشارة (الأحدث، قابلة للتعديل من الإعدادات)
    كاملة التفاصيل، والباقي يظهر كبطاقة "مموّهة" (رمز/اتجاه/ثقة بس، بدون
    دخول/وقف/هدف) خلف قفل اشتراك — مو حجب كامل، تحفيز اشتراك حقيقي.
    """
    try:
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        signals = (
            db.query(Signal)
            .filter(
                Signal.status.in_(["PENDING", "ACTIVE"]),
                Signal.created_at >= cutoff,
            )
            .order_by(Signal.created_at.desc())
            .limit(limit)
            .all()
        )

        full_access = _has_full_signal_access(user)
        free_limit  = _trial_signal_daily_limit(db)
        unlimited   = free_limit <= 0   # 0 = غير محدود، بنفس اتفاقية باقي حدود لوحة الإدارة

        data = []
        for i, s in enumerate(signals):
            unlocked = full_access or unlimited or i < free_limit
            item = {
                "id":               s.id,
                "symbol":           s.market,
                "market":           s.market,
                "timeframe":        s.timeframe,
                "recommendation":   s.signal_type.value if hasattr(s.signal_type, 'value') else s.signal_type,
                "signal_type":      s.signal_type.value if hasattr(s.signal_type, 'value') else s.signal_type,
                "status":           s.status.value if hasattr(s.status, 'value') else s.status,
                "ai_confidence":    s.ai_confidence,
                "ai_confidence_score": s.ai_confidence,
                "created_at":       s.created_at.isoformat(),
                "locked":           not unlocked,
            }
            if unlocked:
                item.update({
                    "entry_price":      s.entry_price,
                    "stop_loss":        s.stop_loss,
                    "take_profit_1":    s.take_profit_1,
                    "take_profit_2":    s.take_profit_2,
                    "risk_reward_ratio": s.risk_reward_ratio,
                })
            else:
                item.update({
                    "entry_price": None, "stop_loss": None,
                    "take_profit_1": None, "take_profit_2": None,
                    "risk_reward_ratio": None,
                })
            data.append(item)

        return {
            "success": True,
            "count": len(data),
            "full_access": full_access,
            "free_limit": free_limit,
            "data": data,
        }

    except Exception as e:
        logger.error(f"❌ Error fetching signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_signal_history(
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """سجل التوصيات مع حالة التتبع"""
    now = datetime.now(timezone.utc)
    signals = (
        db.query(Signal)
        .filter(Signal.user_id == user.id)
        .order_by(Signal.created_at.desc())
        .limit(limit)
        .all()
    )
    result = []
    for s in signals:
        # تحقق من الانتهاء تلقائياً
        if s.status == SignalStatus.ACTIVE and s.expires_at and s.expires_at < now:
            s.status = SignalStatus.EXPIRED
            db.commit()
        result.append({
            "id":          s.id,
            "market":      s.market,
            "timeframe":   s.timeframe,
            "type":        s.signal_type.value if hasattr(s.signal_type, 'value') else s.signal_type,
            "status":      s.status.value if hasattr(s.status, 'value') else s.status,
            "confidence":  s.ai_confidence,
            "entry":       s.entry_price,
            "sl":          s.stop_loss,
            "tp1":         s.take_profit_1,
            "tp2":         s.take_profit_2,
            "rr":          s.risk_reward_ratio,
            "quality":     s.signal_quality.value if hasattr(s.signal_quality, 'value') else s.signal_quality,
            "created_at":  s.created_at.isoformat() if s.created_at else None,
            "expires_at":  s.expires_at.isoformat() if s.expires_at else None,
        })
    return {"signals": result}


@router.get("/performance")
async def get_signal_performance(
    db: Session = Depends(get_db)
):
    """إحصائيات أداء الإشارات (أسبوعية + يومية) — عامة لجميع المستخدمين"""
    from datetime import date, time as dt_time

    now_utc = datetime.now(timezone.utc)
    today   = now_utc.date()

    # Current ISO week
    iso_year, iso_week, _ = today.isocalendar()

    # Closed statuses only for stats
    closed = [SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT]

    # ── Helper: fetch closed signals in date range ──
    def _signals_in_range(start_dt, end_dt):
        return (
            db.query(Signal)
            .filter(
                Signal.status.in_(closed),
                Signal.exit_executed >= start_dt,
                Signal.exit_executed < end_dt,
            )
            .all()
        )

    # ── Current week ──
    week_start = datetime.combine(
        today - timedelta(days=today.weekday()), dt_time(0, 0, 0)
    ).replace(tzinfo=timezone.utc)
    week_end = week_start + timedelta(days=7)

    week_signals = _signals_in_range(week_start, week_end)
    wins   = [s for s in week_signals if (s.points_earned or 0) > 0]
    losses = [s for s in week_signals if (s.points_earned or 0) < 0]
    total_points = sum(s.points_earned or 0 for s in week_signals)
    win_points   = sum(s.points_earned or 0 for s in wins)
    loss_points  = sum(s.points_earned or 0 for s in losses)

    current_week = {
        "week_label":    f"الأسبوع {iso_week} / {iso_year}",
        "total_points":  round(total_points, 2),
        "win_points":    round(win_points, 2),
        "loss_points":   round(loss_points, 2),
        "total_trades":  len(week_signals),
        "wins":          len(wins),
        "losses":        len(losses),
    }

    # ── Daily stats: last 14 days ──
    daily_stats = []
    for i in range(13, -1, -1):
        day = today - timedelta(days=i)
        day_start = datetime.combine(day, dt_time(0, 0, 0)).replace(tzinfo=timezone.utc)
        day_end   = day_start + timedelta(days=1)
        day_sigs  = _signals_in_range(day_start, day_end)
        day_wins  = [s for s in day_sigs if (s.points_earned or 0) > 0]
        day_losses= [s for s in day_sigs if (s.points_earned or 0) < 0]
        trades_detail = [
            {
                "id":     s.id,
                "market": s.market,
                "type":   s.signal_type.value if hasattr(s.signal_type, 'value') else s.signal_type,
                "status": s.status.value if hasattr(s.status, 'value') else s.status,
                "points": round(s.points_earned or 0, 2),
                "entry":  s.entry_price,
                "exit":   s.exit_executed.isoformat() if s.exit_executed else None,
            }
            for s in day_sigs
        ]
        daily_stats.append({
            "date":          day.isoformat(),
            "points":        round(sum(s.points_earned or 0 for s in day_sigs), 2),
            "trades":        len(day_sigs),
            "wins":          len(day_wins),
            "losses":        len(day_losses),
            "trades_detail": trades_detail,
        })

    # ── Weekly stats: last 8 weeks ──
    weekly_stats = []
    for w in range(7, -1, -1):
        wk_start = week_start - timedelta(weeks=w)
        wk_end   = wk_start + timedelta(days=7)
        wk_sigs  = _signals_in_range(wk_start, wk_end)
        wk_wins  = [s for s in wk_sigs if (s.points_earned or 0) > 0]
        wk_losses= [s for s in wk_sigs if (s.points_earned or 0) < 0]
        wk_pts   = sum(s.points_earned or 0 for s in wk_sigs)
        wk_iso   = wk_start.isocalendar()
        weekly_stats.append({
            "week":          f"W{wk_iso[1]}/{wk_iso[0]}",
            "total_points":  round(wk_pts, 2),
            "win_points":    round(sum(s.points_earned or 0 for s in wk_wins), 2),
            "loss_points":   round(sum(s.points_earned or 0 for s in wk_losses), 2),
            "total_trades":  len(wk_sigs),
            "wins":          len(wk_wins),
            "losses":        len(wk_losses),
        })

    return {
        "current_week": current_week,
        "daily_stats":  daily_stats,
        "weekly_stats": weekly_stats,
    }


@router.get("/public-results")
def get_public_results(db: Session = Depends(get_db)):
    """
    آخر الصفقات المغلقة + إحصائيات الأسبوع — عامة للزوار (Proof of Performance)
    لا تحتوي على بيانات شخصية
    """
    from datetime import date, time as dt_time

    now_utc   = datetime.now(timezone.utc)
    today     = now_utc.date()
    week_start = datetime.combine(
        today - timedelta(days=today.weekday()), dt_time(0, 0, 0)
    ).replace(tzinfo=timezone.utc)

    closed_statuses = [SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT]

    # ── Last 12 closed trades (most recent first) ──
    recent = (
        db.query(Signal)
        .filter(Signal.status.in_(closed_statuses))
        .order_by(Signal.exit_executed.desc())
        .limit(12)
        .all()
    )

    trades = []
    for s in recent:
        status_val = s.status.value if hasattr(s.status, "value") else str(s.status)
        type_val   = s.signal_type.value if hasattr(s.signal_type, "value") else str(s.signal_type)
        pts        = round(s.points_earned or 0, 1)
        is_win     = pts > 0
        trades.append({
            "market":   s.market or "—",
            "type":     type_val,
            "result":   status_val,
            "points":   pts,
            "win":      is_win,
            "closed_at": s.exit_executed.strftime("%Y-%m-%d") if s.exit_executed else None,
        })

    # ── Week stats ──
    week_sigs = (
        db.query(Signal)
        .filter(
            Signal.status.in_(closed_statuses),
            Signal.exit_executed >= week_start,
        )
        .all()
    )
    wins   = [s for s in week_sigs if (s.points_earned or 0) > 0]
    losses = [s for s in week_sigs if (s.points_earned or 0) < 0]
    total_pts   = round(sum(s.points_earned or 0 for s in week_sigs), 1)
    win_rate    = round(len(wins) / len(week_sigs) * 100) if week_sigs else 0
    best_trade  = max((s.points_earned or 0 for s in wins), default=0)

    # ── All-time totals ──
    all_closed = db.query(Signal).filter(Signal.status.in_(closed_statuses)).all()
    all_wins   = [s for s in all_closed if (s.points_earned or 0) > 0]
    all_rate   = round(len(all_wins) / len(all_closed) * 100) if all_closed else 0

    return {
        "trades": trades,
        "week": {
            "wins":       len(wins),
            "losses":     len(losses),
            "total":      len(week_sigs),
            "points":     total_pts,
            "win_rate":   win_rate,
            "best_trade": round(best_trade, 1),
        },
        "all_time": {
            "total":    len(all_closed),
            "wins":     len(all_wins),
            "win_rate": all_rate,
        },
    }




@router.get("/scorecard")
def signals_scorecard(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """لوحة أداء الإشارات — نسبة الفوز لكل رمز"""
    closed_statuses = [SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT]

    all_signals = db.query(Signal).filter(
        Signal.status.in_(closed_statuses + [SignalStatus.ACTIVE, SignalStatus.EXPIRED])
    ).all()

    stats: dict = {}
    for sig in all_signals:
        m = sig.market
        if m not in stats:
            stats[m] = {"wins": 0, "losses": 0, "active": 0, "expired": 0}
        if sig.status in (SignalStatus.TP1_HIT, SignalStatus.TP2_HIT):
            stats[m]["wins"] += 1
        elif sig.status == SignalStatus.SL_HIT:
            stats[m]["losses"] += 1
        elif sig.status == SignalStatus.ACTIVE:
            stats[m]["active"] += 1
        else:
            stats[m]["expired"] += 1

    result = []
    total_wins = total_losses = 0
    for market, d in sorted(stats.items()):
        resolved = d["wins"] + d["losses"]
        win_rate = round(d["wins"] / resolved * 100) if resolved > 0 else None
        total_wins   += d["wins"]
        total_losses += d["losses"]
        result.append({
            "market":   market,
            "wins":     d["wins"],
            "losses":   d["losses"],
            "active":   d["active"],
            "total":    resolved + d["active"] + d["expired"],
            "win_rate": win_rate,
        })

    total_resolved = total_wins + total_losses
    overall_win_rate = round(total_wins / total_resolved * 100) if total_resolved > 0 else None

    return {
        "scorecard": result,
        "overall": {
            "wins":     total_wins,
            "losses":   total_losses,
            "win_rate": overall_win_rate,
            "total":    len(all_signals),
        }
    }


@router.get("/backtest")
def signals_backtest(
    symbol:    str = "",
    timeframe: str = "",
    days:      int = 90,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Backtesting Lite — أداء الإشارات التاريخية.
    يمكن الفلترة بـ symbol و timeframe والمدة الزمنية (days).
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    closed = [SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT]

    q = db.query(Signal).filter(
        Signal.status.in_(closed),
        Signal.created_at >= since,
    )
    if symbol:
        q = q.filter(Signal.market == symbol.upper())
    if timeframe:
        q = q.filter(Signal.timeframe == timeframe)

    sigs = q.order_by(Signal.created_at.desc()).all()

    # ── Aggregate by symbol ──────────────────────────────────────────────────
    by_symbol: dict = {}
    by_tf: dict = {}
    rr_values = []

    for s in sigs:
        m  = s.market or "?"
        tf = s.timeframe or "?"
        win = s.status in (SignalStatus.TP1_HIT, SignalStatus.TP2_HIT)

        # by symbol
        if m not in by_symbol:
            by_symbol[m] = {"wins": 0, "losses": 0, "rr_sum": 0.0, "signals": []}
        by_symbol[m]["wins" if win else "losses"] += 1
        rr = float(s.risk_reward_ratio or 0)
        by_symbol[m]["rr_sum"] += rr if win else 0

        # by timeframe
        if tf not in by_tf:
            by_tf[tf] = {"wins": 0, "losses": 0}
        by_tf[tf]["wins" if win else "losses"] += 1

        if rr > 0:
            rr_values.append(rr if win else -rr)

        # last 5 signals preview
        if len(by_symbol[m]["signals"]) < 5:
            by_symbol[m]["signals"].append({
                "id":         s.id,
                "direction":  s.signal_type,
                "status":     s.status.value if s.status else "",
                "entry":      s.entry_price,
                "rr":         rr,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            })

    # ── Build result ──────────────────────────────────────────────────────────
    symbol_rows = []
    for m, d in sorted(by_symbol.items()):
        resolved = d["wins"] + d["losses"]
        wr = round(d["wins"] / resolved * 100, 1) if resolved > 0 else None
        avg_rr = round(d["rr_sum"] / d["wins"], 2) if d["wins"] > 0 else None
        symbol_rows.append({
            "symbol":        m,
            "wins":          d["wins"],
            "losses":        d["losses"],
            "total":         resolved,
            "win_rate":      wr,
            "avg_winning_rr": avg_rr,
            "recent":        d["signals"],
        })

    tf_rows = []
    for tf, d in sorted(by_tf.items()):
        resolved = d["wins"] + d["losses"]
        wr = round(d["wins"] / resolved * 100, 1) if resolved > 0 else None
        tf_rows.append({"timeframe": tf, "wins": d["wins"], "losses": d["losses"], "win_rate": wr})

    total_wins   = sum(d["wins"]   for d in by_symbol.values())
    total_losses = sum(d["losses"] for d in by_symbol.values())
    total_res    = total_wins + total_losses
    avg_rr_all   = round(sum(rr_values) / len(rr_values), 2) if rr_values else None

    return {
        "filter": {"symbol": symbol or "ALL", "timeframe": timeframe or "ALL", "days": days},
        "overall": {
            "total":    total_res,
            "wins":     total_wins,
            "losses":   total_losses,
            "win_rate": round(total_wins / total_res * 100, 1) if total_res > 0 else None,
            "avg_rr":   avg_rr_all,
        },
        "by_symbol":    symbol_rows,
        "by_timeframe": tf_rows,
    }


# ── Must be LAST — catches /{signal_id} after all static routes ──────────────
@router.get("/{signal_id}")
async def get_signal_details(
    signal_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed signal information"""
    try:
        signal = db.query(Signal).filter(Signal.id == signal_id).first()
        if not signal:
            raise HTTPException(status_code=404, detail="Signal not found")
        return {
            "success": True,
            "data": {
                "id": signal.id,
                "market": signal.market,
                "timeframe": signal.timeframe,
                "signal_type": signal.signal_type.value,
                "signal_quality": signal.signal_quality.value,
                "status": signal.status.value,
                "entry_price": signal.entry_price,
                "stop_loss": signal.stop_loss,
                "take_profit_1": signal.take_profit_1,
                "take_profit_2": signal.take_profit_2,
                "current_price": signal.current_price,
                "ai_confidence": signal.ai_confidence,
                "ai_reasoning": signal.ai_reasoning,
                "wyckoff_phase": signal.wyckoff_phase,
                "premium_discount": signal.premium_discount,
                "killzone": signal.killzone,
                "risk_reward_ratio": signal.risk_reward_ratio,
                "profit_loss": signal.profit_loss,
                "profit_loss_percentage": signal.profit_loss_percentage,
                "created_at": signal.created_at.isoformat(),
                "expires_at": signal.expires_at.isoformat() if signal.expires_at else None,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching signal details: {e}")
        raise HTTPException(status_code=500, detail=str(e))
