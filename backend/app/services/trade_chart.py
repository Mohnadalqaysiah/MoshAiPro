"""
شارت التحقق من صفقة (2026-10-24، طلب المالك: "المستخدم يقدر يشوف الصفقات القديمة … لكي يتحقق").

يعرض الشموع الحقيقية لفترة الصفقة مع خطوط الدخول والوقف والأهداف، فيرى العميل بعينه أين وصل السعر دون أن يثق بكلامنا.

**مرجع الأسعار = نفس مرجع حلقة الرصد والتحقق** (admin._verify_signal_outcome_core — مكرّر عمداً هنا بدل لمس مسار الأدمن):
الذهب والفضة مستوياتهما فورية ← شموع TradingView الفورية (OANDA)، ولا سقوط للآجل (GC=F/SI=F أعلى بـbasis ~$60 للذهب —
شارت بمرجع مختلف يُظهر ملامسات لم تحدث). بقية الرموز ← get_ohlcv (نفس مرجع مستوياتها).
الفاصل يُختار بعمر الصفقة لأن المصادر تعطي آخر N شمعة فقط: 5m حتى ~3 أيام، 1h حتى ~40 يوماً، ثم 1d.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

SPOT_ADJUSTED = {"XAUUSD", "XAGUSD"}
CLOSED = ("TP1_HIT", "TP2_HIT", "SL_HIT", "BREAKEVEN", "EXPIRED")
_STEP = {"5m": timedelta(minutes=5), "1h": timedelta(hours=1), "1d": timedelta(days=1)}


def _aware(d: Optional[datetime]) -> Optional[datetime]:
    return d if d is None or d.tzinfo else d.replace(tzinfo=timezone.utc)


def pick_interval(start: datetime, now: datetime) -> tuple:
    """(الفاصل، عدد الشموع المطلوبة) بحيث تغطي الشموع بداية الصفقة مع هامش قبلها."""
    age = now - start
    if age <= timedelta(hours=78):
        return "5m", 1000
    if age <= timedelta(days=38):
        return "1h", 1000
    return "1d", 400


def window(candles: list, start: datetime, end: datetime, interval: str, before: int = 30, after: int = 15) -> list:
    """شموع من (البداية − before شمعة) إلى (النهاية + after شمعة). candles مرتبة زمنياً: dict فيها t (datetime)."""
    step = _STEP[interval]
    lo, hi = start - step * before, end + step * after
    return [c for c in candles if lo <= c["t"] <= hi]


async def _fetch(market: str, interval: str, bars: int) -> tuple:
    """يُرجع (شموع، المصدر) أو ([]، سبب)."""
    import pandas as pd
    m = market.upper()
    if m in SPOT_ADJUSTED:
        from app.services.tv_price_feed import TV_SYMBOL_MAP, fetch_tv_history
        tv = TV_SYMBOL_MAP.get(m)
        raw = await fetch_tv_history(tv, interval, bars=bars) if tv else None
        if not raw:
            return [], "شموع السعر الفوري غير متاحة الآن لهذا المعدن — أعد المحاولة بعد قليل"
        return [{"t": datetime.fromtimestamp(b[0], tz=timezone.utc), "o": float(b[1]), "h": float(b[2]),
                 "l": float(b[3]), "c": float(b[4])} for b in raw], "TradingView (سعر فوري)"
    from app.services.smart_data import smart_data
    df = await smart_data.get_ohlcv(market, interval, bars=bars)
    if df is None or df.empty:
        return [], "تعذّر جلب بيانات السوق لهذا الرمز"
    out = []
    for _, row in df.iterrows():
        t = pd.Timestamp(row["datetime"])
        t = t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
        out.append({"t": t.to_pydatetime(), "o": float(row["open"]), "h": float(row["high"]),
                    "l": float(row["low"]), "c": float(row["close"])})
    return out, "بيانات السوق"


async def build_chart(signal) -> dict:
    status = getattr(signal.status, "value", signal.status)
    if status not in CLOSED:
        return {"ok": False, "error": "الشارت متاح بعد إغلاق الصفقة"}
    now = datetime.now(timezone.utc)
    start = _aware(signal.created_at)
    end = _aware(signal.exit_executed) or _aware(signal.expires_at) or now
    end = min(end, now)
    interval, bars = pick_interval(start, now)
    candles, source = await _fetch(signal.market, interval, bars)
    if not candles:
        return {"ok": False, "error": source}
    candles.sort(key=lambda c: c["t"])
    win = window(candles, start, end, interval)
    if not win:
        return {"ok": False, "error": "لا توجد شموع لهذه الفترة لدى مصدر البيانات (قد تكون الصفقة أقدم من المتاح)"}
    side = getattr(signal.signal_type, "value", signal.signal_type)
    return {
        "ok": True, "id": signal.id, "market": signal.market, "timeframe": signal.timeframe, "side": side,
        "status": status, "interval": interval, "source": source,
        "entry": signal.entry_price, "sl": signal.stop_loss, "tp1": signal.take_profit_1,
        "tp2": signal.take_profit_2 if signal.take_profit_2 and signal.take_profit_2 != signal.take_profit_1 else None,
        "tp3": signal.take_profit_3, "tp3_hit": bool(signal.tp3_hit_at),
        "opened_at": start.isoformat(), "closed_at": end.isoformat(),
        "candles": [{"t": c["t"].isoformat(), "o": c["o"], "h": c["h"], "l": c["l"], "c": c["c"]} for c in win],
    }
