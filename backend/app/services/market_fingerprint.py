"""
بصمة السوق لحظة الإشارة (2026-10-13) — الخطوة 1 من "المنصة التي تتعلم" (DECISIONS 13/10).

مصدران:
  1) ما حسبه المحرك أصلاً بالتحليل (لا يُعدَّل المحرك؛ نقرأ القاموس الناتج فقط).
  2) قياسات نحسبها هنا من شموع 4h بنفس تعريف فلتر الاتجاه (_ema50_4h_trend): قوة الاتجاه
     وبعد السعر عن EMA50 — وللكريبتو حالة البيتكوين لأن العملات تتحرك معاً.

لا يرمي استثناء أبداً، ولا يؤخر حفظ الإشارة إن فشل: البصمة إضافة للتعلم لا شرط للإرسال.
"""
from datetime import datetime, timezone
from typing import Optional

from loguru import logger

FEATURES_VERSION = 1
_pending: set = set()


def _g(d, *path, default=None):
    for p in path:
        if not isinstance(d, dict):
            return default
        d = d.get(p)
    return d if d is not None else default


def _num(v):
    try:
        return round(float(v), 6)
    except (TypeError, ValueError):
        return None


def from_analysis(analysis: dict) -> dict:
    """ما حسبه المحرك — قراءة فقط."""
    a = analysis or {}
    cal = a.get("calibration_params") or {}
    price = _num(a.get("current_price"))
    atr = _num(_g(a, "levels", "atr"))
    return {
        "market_state":     cal.get("market_state"),      # RANGING / TRENDING / VOLATILE
        "market_regime":    cal.get("market_regime"),
        "volatility":       cal.get("volatility"),        # LOW / NORMAL / HIGH
        "atr_pct":          round(atr / price * 100, 4) if atr and price else None,
        "tightening":       bool(_g(cal, "tightening", "active", default=False)),
        "ltf_trend":        _g(a, "market_structure", "trend"),
        "ltf_mode":         _g(a, "market_mode", "mode"),
        "htf_tf":           _g(a, "htf_context", "timeframe"),
        "htf_trend":        _g(a, "htf_context", "trend"),
        "htf_structure":    _g(a, "htf_context", "structure"),
        "htf_pd_zone":      _g(a, "htf_context", "premium_discount"),
        "pd_zone":          _g(a, "premium_discount", "zone"),
        "pd_pct":           _num(_g(a, "premium_discount", "pct")),
        "wyckoff":          _g(a, "wyckoff", "phase"),
        "kill_zone":        _g(a, "kill_zone", "active_session"),
        "momentum":         _g(a, "momentum", "strength"),             # WEAK / ... (ict_engine.detect_momentum)
        "momentum_score":   _num(_g(a, "momentum", "score")),
        "momentum_dir":     _g(a, "momentum", "consecutive_direction"),
        "displacement":     bool(_g(a, "momentum", "is_displacement", default=False)),
        "range_trap":       bool(_g(a, "range_conflict", "in_range_trap", default=False)),
        "confidence":       _num(a.get("ai_confidence_score")),
        "rr":               _num(_g(a, "levels", "risk_reward")),
        "price":            price,
    }


def _trend_metrics(df_4h) -> dict:
    """نفس تعريف _ema50_4h_trend (آخر 6 شموع 4h) + مقادير القوة."""
    if df_4h is None or len(df_4h) < 56:
        return {}
    close = df_4h["close"].astype(float)
    ema = close.ewm(span=50, adjust=False).mean()
    px, e_now, e_then = float(close.iloc[-1]), float(ema.iloc[-1]), float(ema.iloc[-6])
    label = "UP" if px > e_now and e_now > e_then else "DOWN" if px < e_now and e_now < e_then else "FLAT"
    ret_24h = (px / float(close.iloc[-7]) - 1) * 100 if len(close) > 7 else None
    return {
        "trend":        label,
        "dist_ema_pct": round((px / e_now - 1) * 100, 3),      # بعد السعر عن EMA50 (موجب = فوقه)
        "ema_slope_pct": round((e_now / e_then - 1) * 100, 3),  # ميل EMA50 خلال 6 شموع (24 ساعة)
        "ret_24h_pct":  round(ret_24h, 3) if ret_24h is not None else None,
    }


async def _h4(symbol: str) -> dict:
    try:
        from app.services.smart_data import smart_data
        df = await smart_data.get_ohlcv(symbol, "4h", bars=100)
        return _trend_metrics(df)
    except Exception as e:
        logger.debug(f"fingerprint 4h {symbol}: {e}")
        return {}


def schedule(analysis: dict, symbol: str, timeframe: str, signal_type: str,
             signal_id: Optional[int] = None, shadow_id: Optional[int] = None) -> None:
    """يلتقط البصمة بالخلفية (جلسة DB خاصة) — لا يؤخر رد التحليل ولا حفظ الإشارة.
    ما حسبه المحرك يُنسخ الآن (لحظة الإشارة)، وشموع 4h تُجلب بالخلفية خلال ثوانٍ."""
    if not (signal_id or shadow_id):
        return
    try:
        import asyncio
        snap = from_analysis(analysis)
        t = asyncio.get_running_loop().create_task(
            _capture_own_session(snap, symbol, timeframe, signal_type, signal_id, shadow_id))
        _pending.add(t)                    # مرجع حتى لا تُجمع المهمة قبل انتهائها
        t.add_done_callback(_pending.discard)
    except Exception as e:
        logger.warning(f"fingerprint schedule {symbol}: {e}")


async def _capture_own_session(snap, symbol, timeframe, signal_type, signal_id, shadow_id):
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        await capture(db, None, symbol, timeframe, signal_type, signal_id, shadow_id, snapshot=snap)
    finally:
        db.close()


async def capture(db, analysis: Optional[dict], symbol: str, timeframe: str, signal_type: str,
                  signal_id: Optional[int] = None, shadow_id: Optional[int] = None,
                  snapshot: Optional[dict] = None) -> None:
    if not (signal_id or shadow_id):
        return
    try:
        from app.models.signal_feature import SignalFeature
        from app.services.weekend_policy import _crypto_symbols
        f = dict(snapshot) if snapshot is not None else from_analysis(analysis)
        now = datetime.now(timezone.utc)
        f.update({"side": signal_type, "weekday": now.weekday(), "hour_utc": now.hour})
        f["h4"] = await _h4(symbol)
        if f["h4"].get("trend") in ("UP", "DOWN"):
            f["with_h4_trend"] = (f["h4"]["trend"] == "UP") == (signal_type == "BUY")
        if symbol.upper() in _crypto_symbols(db):
            f["is_crypto"] = True
            f["btc_h4"] = f["h4"] if symbol.upper() == "BTCUSD" else await _h4("BTCUSD")
        db.add(SignalFeature(signal_id=signal_id, shadow_id=shadow_id, market=symbol.upper(),
                             timeframe=timeframe, version=FEATURES_VERSION, features=f))
        db.commit()
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        logger.warning(f"fingerprint capture {symbol}/{timeframe}: {e}")
