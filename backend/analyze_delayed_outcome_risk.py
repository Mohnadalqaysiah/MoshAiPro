"""
analyze_delayed_outcome_risk.py
==================================
محاكاة قراءة فقط (لا تعديل) — يحدّد الحجم الحقيقي (مو النظري) لخطر
"نافذة فحص واسعة تحوي كل من SL وTP" اللي أدت لتأخير اكتشاف نتائج
بعض الصفقات ساعات طويلة بعد إغلاقها الحقيقي.

لكل صفقة محسومة منذ 2026-08-18 حيث (exit_executed - created_at) > 4
ساعات: يجيب بيانات 1h حقيقية (نفس مصدر get_ohlcv الحي — yfinance عبر
smart_data، نفس تعيين الرموز الفعلي بالتطبيق)، يمشي شمعة-شمعة من
created_at، ويحدد: هل السعر لمس SL وTP الاثنين بنفس النافذة؟ لو نعم
أيهما جاء أولاً زمنياً، وهل يطابق status المسجّل؟

التشغيل (قراءة فقط، آمن 100% — ما يعدّل أي شيء بقاعدة البيانات):
  docker cp analyze_delayed_outcome_risk.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/analyze_delayed_outcome_risk.py
"""
import sys, asyncio
sys.path.insert(0, "/app")

from datetime import datetime, timedelta, timezone
from app.database import SessionLocal
from app.models.signal import Signal, SignalStatus
from app.services.smart_data import smart_data

CUTOFF = datetime(2026, 8, 18, tzinfo=timezone.utc)
DELAY_THRESHOLD_HOURS = 4
CLOSED = {"TP1_HIT", "TP2_HIT", "SL_HIT"}


async def check_signal(sig) -> dict:
    entry = float(sig.entry_price or 0)
    sl    = float(sig.stop_loss or 0)
    tp1   = float(sig.take_profit_1 or 0)
    tp2   = float(sig.take_profit_2 or tp1)
    is_buy = (sig.signal_type.value if hasattr(sig.signal_type, "value") else sig.signal_type) == "BUY"
    if not (entry and sl and tp1):
        return {"status": "SKIP_MISSING_LEVELS"}

    created = sig.created_at
    exited  = sig.exit_executed
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    if exited.tzinfo is None:
        exited = exited.replace(tzinfo=timezone.utc)

    gap_hours = (exited - created).total_seconds() / 3600
    bars_needed = max(30, int(gap_hours) + 10)

    try:
        df = await smart_data.get_ohlcv(sig.market, "1h", bars=bars_needed)
    except Exception as e:
        return {"status": "FETCH_ERROR", "error": str(e), "gap_hours": gap_hours}

    if df is None or df.empty:
        return {"status": "NO_DATA", "gap_hours": gap_hours}

    import pandas as _pd
    if "datetime" in df.columns:
        ts_series = _pd.to_datetime(df["datetime"], utc=True)
        rows = list(zip(ts_series, df["high"], df["low"]))
    else:
        idx = _pd.to_datetime(df.index, utc=True)
        rows = list(zip(idx, df["high"], df["low"]))

    rows = [r for r in rows if created <= r[0] <= exited + timedelta(hours=1)]
    if not rows:
        return {"status": "NO_DATA_IN_WINDOW", "gap_hours": gap_hours}

    has_tp2 = (tp2 > tp1) if is_buy else (tp2 < tp1)

    sl_first_ts = tp_first_ts = None
    tp_first_status = None
    for ts, hi, lo in rows:
        hi, lo = float(hi), float(lo)
        sl_touch  = (lo <= sl) if is_buy else (hi >= sl)
        tp2_touch = has_tp2 and ((hi >= tp2) if is_buy else (lo <= tp2))
        tp1_touch = (hi >= tp1) if is_buy else (lo <= tp1)
        if sl_touch and sl_first_ts is None:
            sl_first_ts = ts
        if (tp2_touch or tp1_touch) and tp_first_ts is None:
            tp_first_ts = ts
            tp_first_status = "TP2_HIT" if tp2_touch else "TP1_HIT"
        if sl_first_ts is not None and tp_first_ts is not None:
            break

    both_touched = sl_first_ts is not None and tp_first_ts is not None
    if both_touched:
        real_first = "SL_HIT" if sl_first_ts <= tp_first_ts else tp_first_status
    elif sl_first_ts is not None:
        real_first = "SL_HIT"
    elif tp_first_ts is not None:
        real_first = tp_first_status
    else:
        real_first = None

    recorded = sig.status.value if hasattr(sig.status, "value") else sig.status
    match = (real_first == recorded) if real_first else None

    return {
        "status": "OK", "gap_hours": gap_hours, "both_touched": both_touched,
        "sl_first_ts": sl_first_ts.isoformat() if sl_first_ts else None,
        "tp_first_ts": tp_first_ts.isoformat() if tp_first_ts else None,
        "real_first": real_first, "recorded": recorded, "match": match,
    }


async def main():
    db = SessionLocal()
    try:
        rows = (
            db.query(Signal)
            .filter(
                Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT]),
                Signal.created_at >= CUTOFF,
                Signal.exit_executed.isnot(None),
            )
            .all()
        )
        print(f"📊 صفقات محسومة منذ {CUTOFF.date()}: {len(rows)}")

        # فقط قرار واحد لكل (سوق+فريم+نوع+دخول+وقت إنشاء) لتجنّب تكرار نفس القرار لعدة مستخدمين
        seen = set()
        delayed = []
        for s in rows:
            created = s.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            exited = s.exit_executed
            if exited.tzinfo is None:
                exited = exited.replace(tzinfo=timezone.utc)
            key = (s.market, s.timeframe, str(s.signal_type), round(float(s.entry_price or 0), 6), created)
            if key in seen:
                continue
            seen.add(key)
            gap_h = (exited - created).total_seconds() / 3600
            if gap_h > DELAY_THRESHOLD_HOURS:
                delayed.append(s)

        print(f"📊 قرارات فريدة 'متأخرة' (exit - created > {DELAY_THRESHOLD_HOURS}h): {len(delayed)}\n")

        if not delayed:
            print("✅ لا يوجد صفقات متأخرة بهذا المعيار — الخطر غير موجود عملياً بهذه الفترة.")
            return

        results = []
        for i, s in enumerate(delayed):
            if i > 0:
                await asyncio.sleep(0.5)   # تجنّب تقييد معدل الطلبات
            r = await check_signal(s)
            r["id"] = s.id
            r["market"] = s.market
            r["timeframe"] = s.timeframe
            results.append(r)
            tag = ""
            if r["status"] == "OK":
                if r["both_touched"]:
                    tag = "⚠️ لمست الاثنين!" + ("  ❌ MISMATCH" if r["match"] is False else "  ✅ متطابق")
                else:
                    tag = "✅ لمست مستوى واحد بس"
            print(f"  #{s.id:5d} {s.market:10s} {s.timeframe:4s}  gap={r.get('gap_hours',0):.1f}h  "
                  f"[{r['status']}]  {tag}")

        ok_results = [r for r in results if r["status"] == "OK"]
        both = [r for r in ok_results if r["both_touched"]]
        mismatches = [r for r in both if r["match"] is False]

        print("\n" + "="*90)
        print("📊 النتيجة الإجمالية — حجم الخطر الفعلي")
        print("="*90)
        print(f"  إجمالي القرارات المتأخرة المفحوصة: {len(delayed)}")
        print(f"  تحقّقت فعلياً (بيانات متاحة): {len(ok_results)}")
        print(f"  لمست SL وTP الاثنين بنفس النافذة: {len(both)}  "
              f"({len(both)/len(ok_results)*100:.1f}% من المتحقَّق منها)" if ok_results else "")
        print(f"  من هذي، النتيجة المسجّلة لا تطابق الترتيب الزمني الحقيقي (انعكاس فعلي مؤكد): {len(mismatches)}")
        if mismatches:
            print("\n  🚨 الحالات المعكوسة فعلياً:")
            for r in mismatches:
                print(f"     #{r['id']} {r['market']} — مسجّل={r['recorded']} لكن الحقيقي={r['real_first']}")

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
