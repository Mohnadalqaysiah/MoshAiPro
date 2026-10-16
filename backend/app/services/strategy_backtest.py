"""
Strategy Backtest (2026-10-14) — باكتيست حقيقي لاستراتيجيات باني الاستراتيجيات، يراه المستخدم.

كيف يعمل (DECISIONS.md 14/10):
  - يجلب شموعاً تاريخية حقيقية (yfinance — نفس مصدر التحليل الحي) لكل فريم تستخدمه شروط الاستراتيجية.
  - يمشي على شموع الفريم الأصغر **المغلقة** واحدة واحدة. عند كل شمعة يشغّل نفس دالة التحليل الحية
    (ict_engine.full_analysis) على آخر 150 شمعة مغلقة لكل فريم — بلا أي شمعة مستقبلية — ثم نفس
    evaluate_strategy التي تقرّر الإطلاق الحي.
  - الجلسات/الـKill Zones تُحسب بوقت الشمعة التاريخية (مع التوقيت الصيفي) لا بوقت الآن.
  - **غير قابل للاختبار التاريخي ويُعلن:** شرط "اتجاه الصفقة" (قرار المحرك الكامل: معايرة ذاتية وحالة
    لا تُعاد على الماضي) — يُستبعد من منطق المجموعات كأي شرط غير مدعوم، ويُذكر بالنتيجة.
  - الصفقة: دخول بإغلاق شمعة الإطلاق؛ وقف خلف قاع/قمة آخر 10 شموع ± 0.1 ATR؛ TP1 عند 1R (منتج 14/10)؛
    TP2 عند RR الاستراتيجية. **محاسبة قابلة للتنفيذ:** نصف الصفقة يُغلق عند TP1 ويُنقل الوقف للدخول، والنصف
    الآخر حتى TP2. الوقف أولاً إن لُمس الاثنان بنفس الشمعة. أقصى مدة 24 ساعة ثم إغلاق بسعر آخر شمعة.
  - صفقة واحدة مفتوحة لكل رمز (لا إطلاق جديد قبل إغلاق السابقة).
  - المعادن على عقود آجلة (GC=F/SI=F) — نفس مرجع شموع التحليل؛ الأسعار المعروضة آجلة لا فورية.
نتائج الماضي لا تعد بالمستقبل.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from loguru import logger

WINDOW = 150                 # نفس عدد الشموع بالتحليل الحي
SWING_LOOKBACK = 10
MAX_HOLD = timedelta(hours=24)
MAX_SYMBOLS = 3
MAX_DAYS_BY_PRIMARY = {"1m": 3, "5m": 14, "15m": 45, "30m": 55, "1h": 120, "4h": 300, "1d": 700}
_YF_INTERVAL = {"1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1h": "1h", "4h": "1h", "1d": "1d"}
_YF_PERIOD = {"1m": "7d", "5m": "60d", "15m": "60d", "30m": "60d", "1h": "730d", "4h": "730d", "1d": "5y"}

_LOCK = asyncio.Semaphore(1)   # تشغيل واحد بنفس الوقت — يحمي معالج الخادم


# ─── البيانات ─────────────────────────────────────────────────────────────────

def _fetch_history(symbol: str, tf: str) -> Optional[pd.DataFrame]:
    import yfinance as yf
    from app.services.smart_data import _resolve_yf_symbol, smart_data
    df = yf.Ticker(_resolve_yf_symbol(symbol)).history(
        period=_YF_PERIOD.get(tf, "60d"), interval=_YF_INTERVAL.get(tf, "1h"), auto_adjust=True)
    if df is None or len(df) < WINDOW + 10:
        return None
    df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    df.index = pd.to_datetime(df.index, utc=True)
    df = df[["open", "high", "low", "close", "volume"]].dropna(subset=["open", "high", "low", "close"])
    if tf == "4h":
        df = df.resample("4h").agg({"open": "first", "high": "max", "low": "min",
                                    "close": "last", "volume": "sum"}).dropna()
    df = df.reset_index().rename(columns={df.index.name or "index": "datetime", "Datetime": "datetime", "Date": "datetime"})
    if "datetime" not in df.columns:
        df = df.rename(columns={df.columns[0]: "datetime"})
    df["volume"] = df["volume"].fillna(0.0)
    df = smart_data._add_indicators(df)
    from app.services.strategy_engine import tf_minutes
    df["close_t"] = pd.to_datetime(df["datetime"], utc=True) + pd.Timedelta(minutes=tf_minutes(tf))
    return df.reset_index(drop=True)


# ─── لقطة الاستراتيجية (كائنات بسيطة آمنة للتشغيل بخيط منفصل) ─────────────────

def snapshot(strategy) -> Dict:
    groups = [SimpleNamespace(id=g.id, name=g.name, logic=SimpleNamespace(value=g.logic.value),
                              at_least=g.at_least) for g in strategy.groups]
    conds = [SimpleNamespace(id=c.id, group_id=c.group_id, type=c.type, label=c.label, timeframe=c.timeframe,
                             value=c.value, weight=c.weight, enabled=c.enabled, negate=c.negate)
             for g in strategy.groups for c in g.conditions]
    return {"groups": groups, "conditions": conds, "min_score": strategy.min_score,
            "rr": float(strategy.exec_rr or 2.0), "symbols": list(strategy.symbols or []), "name": strategy.name}


def infer_side(conditions) -> Optional[str]:
    """اتجاه الاستراتيجية من قيم شروطها (صاعد/شراء/خصم ← شراء؛ هابط/بيع/علاوة ← بيع). None = مختلط/غير محدد."""
    from app.services.strategy_engine import _direction_hint
    bull = bear = 0
    for c in conditions:
        if not c.enabled or c.negate:
            continue
        v = c.value or ""
        h = _direction_hint(v)
        if c.type == "premium":
            h = "BULL" if ("خصم" in v or "DISCOUNT" in v.upper()) else "BEAR" if ("علاوة" in v or "PREMIUM" in v.upper()) else None
        if h == "BULL":
            bull += 1
        elif h == "BEAR":
            bear += 1
    return "BUY" if bull > bear else "SELL" if bear > bull else None


# ─── محاكاة الصفقة ────────────────────────────────────────────────────────────

def trade_levels(entry: float, lows, highs, atr: float, side: str, rr: float, symbol: str = "") -> Optional[Dict]:
    """قواعد الصفقة نفسها للباكتيست ولتنبيه الاستراتيجية الحي (2026-10-16) — ما اختُبر هو ما يُرسل.
    lows/highs = آخر SWING_LOOKBACK شمعة حتى شمعة الإطلاق شاملة."""
    from app.services.spread_table import typical_spread, MIN_SL_SPREAD_MULT
    atr = float(atr or 0)
    lo, hi = float(min(lows)), float(max(highs))
    buy = side == "BUY"
    sl = (lo - 0.1 * atr) if buy else (hi + 0.1 * atr)
    if (buy and sl >= entry) or (not buy and sl <= entry):
        sl = entry - atr if buy else entry + atr
    # (2026-10-14) حد أدنى للوقف — نتائج القوالب أظهرت وقوفاً بـ1-3 دولار للذهب (شموع آسيا الهادئة)، داخل
    # الضجيج والسبريد. الأكبر بين نصف ATR و3× السبريد المعتاد (نفس قاعدة المحرك SL_INSIDE_SPREAD_NOISE).
    spread = typical_spread(symbol, entry) or 0.0
    min_dist = max(0.5 * atr, MIN_SL_SPREAD_MULT * spread)
    if abs(entry - sl) < min_dist:
        sl = entry - min_dist if buy else entry + min_dist
    risk = abs(entry - sl)
    if risk <= 0:
        return None
    sgn = 1 if buy else -1
    rr2 = max(1.0, rr)
    return {"entry": entry, "sl": sl, "tp1": entry + sgn * risk, "tp2": entry + sgn * rr2 * risk,
            "risk": risk, "spread": spread, "rr2": rr2}


def _simulate(p: pd.DataFrame, i: int, side: str, rr: float, now: datetime, symbol: str = "") -> Optional[Dict]:
    entry = float(p.at[i, "close"])
    lv = trade_levels(entry, p["low"].iloc[max(0, i - SWING_LOOKBACK + 1): i + 1],
                      p["high"].iloc[max(0, i - SWING_LOOKBACK + 1): i + 1], p.at[i, "atr"], side, rr, symbol)
    if lv is None:
        return None
    buy = side == "BUY"
    sl, tp1, tp2, risk, rr2 = lv["sl"], lv["tp1"], lv["tp2"], lv["risk"], lv["rr2"]
    cost_r = lv["spread"] / risk     # (2026-10-14) السبريد يُخصم من كل صفقة بوحدات R
    sgn = 1 if buy else -1
    r_of = lambda px: sgn * (px - entry) / risk
    t0 = p.at[i, "close_t"]
    end = t0 + MAX_HOLD
    half = armed = False
    cur_sl = sl
    last_close, last_t = entry, t0
    for k in range(i + 1, len(p)):
        tk = p.at[k, "close_t"]
        if tk > end:
            break
        h, l, c = float(p.at[k, "high"]), float(p.at[k, "low"]), float(p.at[k, "close"])
        if armed:
            cur_sl = entry
        if (l <= cur_sl) if buy else (h >= cur_sl):
            r = (0.5 + 0.5 * r_of(cur_sl)) if half else -1.0
            return _trade(t0, tk, side, entry, sl, tp1, tp2, "TP1+BE" if half else "SL", r, half, cost_r)
        if (h >= tp2) if buy else (l <= tp2):
            r = 1.0 if rr2 <= 1.0 else 0.5 + 0.5 * rr2
            return _trade(t0, tk, side, entry, sl, tp1, tp2, "TP2", r, True, cost_r)
        if not half and ((h >= tp1) if buy else (l <= tp1)):
            half = armed = True
        last_close, last_t = c, tk
    if last_t < end and end > now:
        return None                         # ما زالت مفتوحة عند نهاية البيانات — لا تُحسب
    r = (0.5 + 0.5 * r_of(last_close)) if half else r_of(last_close)
    return _trade(t0, last_t, side, entry, sl, tp1, tp2, "EXPIRED", r, half, cost_r)


def _trade(t0, t1, side, entry, sl, tp1, tp2, result, r, tp1_hit, cost_r=0.0):
    dp = 5 if entry < 20 else 3 if entry < 1000 else 2
    return {"time": t0.isoformat(), "exit_time": t1.isoformat(), "side": side,
            "entry": round(entry, dp), "sl": round(sl, dp), "tp1": round(tp1, dp), "tp2": round(tp2, dp),
            "result": result, "r": round(float(r) - cost_r, 3), "r_gross": round(float(r), 3),
            "cost_r": round(cost_r, 3), "tp1_hit": bool(tp1_hit)}


# ─── التشغيل ──────────────────────────────────────────────────────────────────

def run_backtest_sync(snap: Dict, symbols: List[str], days: int, progress=None) -> Dict:
    from app.services.ict_engine import ict_engine
    from app.services.strategy_engine import evaluate_strategy, distinct_timeframes, norm_timeframe

    conds, groups = snap["conditions"], snap["groups"]
    enabled = [c for c in conds if c.enabled]
    if not enabled:
        raise ValueError("لا شروط مفعّلة بهذه الاستراتيجية")
    tfs = distinct_timeframes(conds)
    primary = tfs[0]
    max_days = MAX_DAYS_BY_PRIMARY.get(primary, 45)
    notes = []
    if days > max_days:
        notes.append(f"الفترة قُصّرت إلى {max_days} يوماً — حد البيانات التاريخية المتاحة لفريم {primary}.")
        days = max_days
    fixed_side = infer_side(enabled)
    if not fixed_side:
        notes.append("الاستراتيجية لا تحدد اتجاهاً واحداً بقيم شروطها — اتجاه كل صفقة أُخذ من التحليل الفني "
                     "(ICT) لحظة الإطلاق. للأدق: اكتب صاعد/هابط بقيم الشروط.")
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)

    trades, unsupported, funnel = [], {}, {"bars": 0, "triggers": 0, "skipped_open_trade": 0}
    group_pass = {g.name: 0 for g in groups}
    data_range = {}
    logger.disable("app.services.ict_engine")   # آلاف التحليلات — لا نغرق سجل الخادم
    try:
        for si, sym in enumerate(symbols[:MAX_SYMBOLS]):
            ns = sym.replace("/", "").upper()
            data = {}
            for tf in tfs:
                d = _fetch_history(ns, tf)
                if d is None:
                    notes.append(f"{sym}: لا بيانات تاريخية كافية لفريم {tf} — لم يُختبر.")
                    data = None
                    break
                data[tf] = d
            if not data:
                continue
            p = data[primary]
            ct = {tf: data[tf]["close_t"].values for tf in tfs}
            idx = [i for i in range(len(p)) if p.at[i, "close_t"] >= start and p.at[i, "close_t"] <= now and i >= WINDOW - 1]
            if not idx:
                notes.append(f"{sym}: لا شموع ضمن الفترة.")
                continue
            data_range[sym] = {"from": p.at[idx[0], "close_t"].isoformat(), "to": p.at[idx[-1], "close_t"].isoformat()}
            cache = {}
            busy_until = None
            for n, i in enumerate(idx):
                t = p.at[i, "close_t"]
                funnel["bars"] += 1
                if progress and n % 50 == 0:
                    progress(int(100 * (si + n / len(idx)) / max(1, min(len(symbols), MAX_SYMBOLS))))
                analyses, ict_dir = {}, None
                for tf in tfs:
                    j = int(np.searchsorted(ct[tf], np.datetime64(t.to_datetime64()), side="right")) - 1
                    if j < WINDOW - 1:
                        continue
                    key = (tf, j)
                    if key not in cache:
                        win = data[tf].iloc[j - WINDOW + 1: j + 1].reset_index(drop=True)
                        cache[key] = ict_engine.full_analysis(win, ns, tf)
                    a = dict(cache[key])
                    a["kill_zone"] = ict_engine.get_kill_zone(at=t.to_pydatetime())
                    a["_eval_time_utc"] = t.to_pydatetime()
                    rec = a.pop("recommendation", None)      # قرار المحرك الكامل غير قابل للإعادة تاريخياً
                    if tf == primary:
                        ict_dir = rec
                    analyses[norm_timeframe(tf)] = a
                res = evaluate_strategy(groups, conds, analyses, snap["min_score"], float(p.at[i, "close"]))
                for u in res["unsupported"]:
                    unsupported[u["label"]] = u["type"]
                for g in res["groups_detail"]:
                    if g["passed"]:
                        group_pass[g["name"]] = group_pass.get(g["name"], 0) + 1
                if not res["triggered"]:
                    continue
                funnel["triggers"] += 1
                if busy_until is not None and t < busy_until:
                    funnel["skipped_open_trade"] += 1
                    continue
                side = fixed_side or (ict_dir if ict_dir in ("BUY", "SELL") else None)
                if not side:
                    continue
                tr = _simulate(p, i, side, snap["rr"], now, ns)
                if tr is None:
                    continue
                tr["symbol"] = sym
                tr["conditions"] = [m["label"] for m in res["matched"] if m["hit"]][:8]
                trades.append(tr)
                busy_until = pd.Timestamp(tr["exit_time"])
            cache.clear()
    finally:
        logger.enable("app.services.ict_engine")

    if "direction" in unsupported.values():
        notes.append("شرط \"اتجاه الصفقة\" لا يمكن اختباره تاريخياً (يعتمد على قرار المحرك الكامل اللحظي) — "
                     "استُبعد من منطق المجموعات بهذا الباكتيست.")
    return _summarize(trades, funnel, group_pass, unsupported, notes, days, primary, tfs, fixed_side,
                      snap["rr"], data_range)


def _summarize(trades, funnel, group_pass, unsupported, notes, days, primary, tfs, side, rr, data_range):
    rs = [t["r"] for t in trades]
    n = len(rs)
    eq, peak, dd = 0.0, 0.0, 0.0
    streak = worst_streak = 0
    for r in rs:
        eq += r
        peak = max(peak, eq)
        dd = min(dd, eq - peak)
        streak = streak + 1 if r < 0 else 0
        worst_streak = max(worst_streak, streak)
    weekly = {}
    for t in trades:
        y, w, _ = datetime.fromisoformat(t["time"]).isocalendar()
        k = f"{y}-W{w:02d}"
        wk = weekly.setdefault(k, {"week": k, "trades": 0, "r": 0.0, "wins": 0})
        wk["trades"] += 1
        wk["r"] = round(wk["r"] + t["r"], 3)
        wk["wins"] += t["r"] > 0
    return {
        "summary": {
            "trades": n,
            "tp1_hit_rate": round(100 * sum(t["tp1_hit"] for t in trades) / n, 1) if n else None,
            "win_rate": round(100 * sum(1 for r in rs if r > 0) / n, 1) if n else None,
            "loss_rate": round(100 * sum(1 for r in rs if r < 0) / n, 1) if n else None,
            "total_r": round(sum(rs), 2),
            "avg_r": round(sum(rs) / n, 3) if n else None,
            "max_drawdown_r": round(dd, 2),
            "worst_losing_streak": worst_streak,
            "tp2_hits": sum(1 for t in trades if t["result"] == "TP2"),
            "total_r_gross": round(sum(t.get("r_gross", t["r"]) for t in trades), 2),
            "avg_cost_r": round(sum(t.get("cost_r", 0) for t in trades) / n, 3) if n else None,
        },
        "weekly": sorted(weekly.values(), key=lambda x: x["week"]),
        "trades": trades[-200:],
        "funnel": funnel,
        "group_pass": group_pass,
        "unsupported": [{"label": k, "type": v} for k, v in unsupported.items()],
        "notes": notes,
        "config": {"days": days, "primary_tf": primary, "timeframes": tfs, "side": side or "AUTO",
                   "rr_tp2": rr, "tp1_r": 1.0, "management": "half_at_tp1_then_breakeven",
                   "sl_rule": f"swing {SWING_LOOKBACK} bars ± 0.1 ATR, min max(0.5 ATR, 3x spread)", "max_hold_hours": 24,
                   "costs": "typical spread deducted per trade",
                   "data_range": data_range},
    }


async def run_backtest_job(backtest_id: int):
    from app.database import SessionLocal
    from app.models.strategy import Strategy
    from app.models.strategy_backtest import StrategyBacktest
    async with _LOCK:
        db = SessionLocal()
        try:
            bt = db.query(StrategyBacktest).get(backtest_id)
            if not bt:
                return
            s = db.query(Strategy).filter(Strategy.id == bt.strategy_id).first()
            if not s:
                bt.status, bt.error = "error", "الاستراتيجية غير موجودة"
                db.commit()
                return
            snap = snapshot(s)
            params = bt.params or {}
            symbols = params.get("symbols") or snap["symbols"] or ["XAU/USD"]
            days = int(params.get("days") or 30)
            bt.status = "running"
            db.commit()

            def _progress(pct):
                d2 = SessionLocal()
                try:
                    d2.query(StrategyBacktest).filter(StrategyBacktest.id == backtest_id).update({"progress": max(1, min(99, pct))})
                    d2.commit()
                finally:
                    d2.close()

            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, run_backtest_sync, snap, symbols, days, _progress)
            bt = db.query(StrategyBacktest).get(backtest_id)
            bt.result, bt.status, bt.progress = result, "done", 100
            bt.finished_at = datetime.now(timezone.utc)
            db.commit()
            logger.info(f"📈 Backtest #{backtest_id} done: {result['summary']['trades']} trades")
        except Exception as e:
            logger.exception(f"Backtest #{backtest_id} failed: {e}")
            db.rollback()
            bt = db.query(StrategyBacktest).get(backtest_id)
            if bt:
                bt.status, bt.error = "error", str(e)[:500]
                bt.finished_at = datetime.now(timezone.utc)
                db.commit()
        finally:
            db.close()
