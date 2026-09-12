"""
verify_sl_tp_order_fix.py
============================
تحقق قراءة فقط (لا تعديل) — يعيد بناء نفس المنطق الزمني الجديد
(شمعة-شمعة، الأقدم للأحدث، يتوقف عند أول تطابق) اللي طُبّق بـ
bot_check_outcomes ضد نفس بيانات OHLC الحقيقية، على القرارات الثلاث
المؤكد انعكاسها (analyze_delayed_outcome_risk.py):
  - #2168 XAUUSD 4h  (مسجّل سابقاً: SL_HIT، الحقيقي: TP1_HIT)
  - #2269 SNB    15m (مسجّل سابقاً: TP2_HIT، الحقيقي: SL_HIT)
  - #2164 XAGUSD 1h  (مسجّل سابقاً: TP2_HIT، الحقيقي: SL_HIT)

يتأكد إن المنطق الجديد يعطي النتيجة الصحيحة (المطابقة للواقع) لكل
واحدة قبل ما نثق فيه لتصحيح البيانات التاريخية.

التشغيل:
  docker cp verify_sl_tp_order_fix.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/verify_sl_tp_order_fix.py 2>/dev/null
"""
import sys, asyncio
sys.path.insert(0, "/app")

from datetime import datetime, timedelta, timezone
from app.database import SessionLocal
from app.models.signal import Signal
from app.services.smart_data import smart_data

EXPECTED = {
    2168: "TP1_HIT",
    2269: "SL_HIT",
    2164: "SL_HIT",
}


async def chronological_check(market, entry, sl, tp1, tp2, is_buy, created):
    now = datetime.now(timezone.utc)
    hours_since_created = (now - created).total_seconds() / 3600
    bars_needed = max(30, int(hours_since_created) + 10)
    df = await smart_data.get_ohlcv(market, "1h", bars=bars_needed)
    if df is None or df.empty:
        return None, "NO_DATA"

    import pandas as _pd
    if "datetime" in df.columns:
        ts_series = _pd.to_datetime(df["datetime"], utc=True)
        rows = list(zip(ts_series, df["high"], df["low"]))
    else:
        idx = _pd.to_datetime(df.index, utc=True)
        rows = list(zip(idx, df["high"], df["low"]))

    rows = [r for r in rows if r[0] >= created]
    rows.sort(key=lambda r: r[0])
    if not rows:
        return None, "NO_DATA_IN_WINDOW"

    has_tp2 = (tp2 > tp1) if is_buy else (tp2 < tp1)
    for ts, hi, lo in rows:
        hi, lo = float(hi), float(lo)
        sl_touch  = (lo <= sl) if is_buy else (hi >= sl)
        tp2_touch = has_tp2 and ((hi >= tp2) if is_buy else (lo <= tp2))
        tp1_touch = (hi >= tp1) if is_buy else (lo <= tp1)
        if sl_touch:
            return "SL_HIT", ts
        if tp2_touch:
            return "TP2_HIT", ts
        if tp1_touch:
            return "TP1_HIT", ts
    return None, "NO_TOUCH"


async def main():
    db = SessionLocal()
    try:
        rows = db.query(Signal).filter(Signal.id.in_(list(EXPECTED.keys()))).all()
        by_id = {s.id: s for s in rows}

        all_pass = True
        for sid, expected in EXPECTED.items():
            s = by_id.get(sid)
            if not s:
                print(f"#{sid}: ⚠️ الصف غير موجود بقاعدة البيانات")
                all_pass = False
                continue
            entry = float(s.entry_price)
            sl    = float(s.stop_loss)
            tp1   = float(s.take_profit_1)
            tp2   = float(s.take_profit_2 or tp1)
            is_buy = (s.signal_type.value if hasattr(s.signal_type, "value") else s.signal_type) == "BUY"
            created = s.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)

            result, detail = await chronological_check(s.market, entry, sl, tp1, tp2, is_buy, created)
            ok = (result == expected)
            all_pass = all_pass and ok
            print(f"#{sid} {s.market} ({s.timeframe}): متوقع={expected}  المنطق الجديد={result or detail}  "
                  f"{'✅ PASS' if ok else '❌ FAIL'}")
            await asyncio.sleep(0.5)

        print("\n" + ("✅ كل الحالات الثلاث ناجحة — المنطق الجديد يعطي النتيجة الصحيحة."
                       if all_pass else "❌ فيه حالة فاشلة — لا تعتمد على الإصلاح قبل المراجعة."))
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
