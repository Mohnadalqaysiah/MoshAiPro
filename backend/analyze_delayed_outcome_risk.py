"""
analyze_delayed_outcome_risk.py
==================================
محاكاة قراءة فقط (لا تعديل) — يحدّد الحجم الحقيقي (مو النظري) لخطر
"نافذة فحص واسعة تحوي كل من SL وTP" اللي أدت لتأخير اكتشاف نتائج
بعض الصفقات ساعات طويلة بعد إغلاقها الحقيقي.

(2026-09-12) v2 — يستخدم group_unique_decisions() من
decision_grouping.py (نفس نافذة الدقيقتين المستخدمة بكل تقارير الأداء
بالتطبيق) بدل تجميع مبسّط خاص كان يعتمد على تطابق created_at الحرفي —
النسخة الأولى كانت ممكن تفرّق قرار واحد لعدة "قرارات" بسبب فروق
مايكروثانية بين صفوف نفس القرار لمستخدمين مختلفين.

لكل قرار فريد محسوم منذ 2026-08-18 حيث (exit_executed - created_at) >
4 ساعات: يجيب بيانات 1h حقيقية (نفس مصدر get_ohlcv الحي)، يمشي شمعة-
شمعة من created_at، ويحدد: هل السعر لمس SL وTP الاثنين بنفس النافذة؟
لو نعم أيهما جاء أولاً زمنياً، وهل يطابق status المسجّل.

التشغيل (قراءة فقط، آمن 100% — ما يعدّل أي شيء بقاعدة البيانات):
  docker cp analyze_delayed_outcome_risk.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/analyze_delayed_outcome_risk.py 2>/dev/null
"""
import sys, asyncio
sys.path.insert(0, "/app")

from datetime import datetime, timedelta, timezone
from app.database import SessionLocal
from app.models.signal import Signal, SignalStatus
from app.services.smart_data import smart_data
from app.services.decision_grouping import group_unique_decisions

CUTOFF = datetime(2026, 8, 18, tzinfo=timezone.utc)
DELAY_THRESHOLD_HOURS = 4
CLOSED = {"TP1_HIT", "TP2_HIT", "SL_HIT"}


async def check_decision(market, entry, sl, tp1, tp2, is_buy, created, exited) -> dict:
    now = datetime.now(timezone.utc)
    hours_since_created = (now - created).total_seconds() / 3600
    bars_needed = max(30, int(hours_since_created) + 10)

    try:
        df = await smart_data.get_ohlcv(market, "1h", bars=bars_needed)
    except Exception as e:
        return {"status": "FETCH_ERROR", "error": str(e)}

    if df is None or df.empty:
        return {"status": "NO_DATA"}

    import pandas as _pd
    if "datetime" in df.columns:
        ts_series = _pd.to_datetime(df["datetime"], utc=True)
        rows = list(zip(ts_series, df["high"], df["low"]))
    else:
        idx = _pd.to_datetime(df.index, utc=True)
        rows = list(zip(idx, df["high"], df["low"]))

    rows = [r for r in rows if created <= r[0] <= exited + timedelta(hours=1)]
    if not rows:
        return {"status": "NO_DATA_IN_WINDOW"}

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

    return {
        "status": "OK", "both_touched": both_touched,
        "sl_first_ts": sl_first_ts.isoformat() if sl_first_ts else None,
        "tp_first_ts": tp_first_ts.isoformat() if tp_first_ts else None,
        "real_first": real_first,
    }


async def main():
    db = SessionLocal()
    try:
        raw = (
            db.query(Signal)
            .filter(
                Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT]),
                Signal.created_at >= CUTOFF,
                Signal.exit_executed.isnot(None),
            )
            .all()
        )
        print(f"📊 صفوف خام محسومة منذ {CUTOFF.date()}: {len(raw)}")

        decisions = group_unique_decisions(raw)
        print(f"📊 قرارات فريدة (تجميع صحيح بنافذة دقيقتين، نفس decision_grouping.py): {len(decisions)}")

        # نجيب entry/sl/tp1/tp2 للصف الممثّل (rep) لكل قرار — group_unique_decisions
        # ما يرجّعهم بالـdict، لازم نجيبهم من الصف الأصلي بـid الممثّل
        rep_ids = [d["id"] for d in decisions]
        rep_rows = {s.id: s for s in db.query(Signal).filter(Signal.id.in_(rep_ids)).all()}

        delayed = []
        for d in decisions:
            created = d["created_at"]
            exited  = d["exit_executed"]
            if not created or not exited:
                continue
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if exited.tzinfo is None:
                exited = exited.replace(tzinfo=timezone.utc)
            gap_h = (exited - created).total_seconds() / 3600
            if gap_h > DELAY_THRESHOLD_HOURS:
                rep = rep_rows.get(d["id"])
                if not rep:
                    continue
                delayed.append((d, rep, created, exited, gap_h))

        print(f"📊 قرارات فريدة 'متأخرة' (exit - created > {DELAY_THRESHOLD_HOURS}h): {len(delayed)}  "
              f"(إجمالي صفوف/مستخدمين متأثرين: {sum(d['user_count'] for d,_,_,_,_ in delayed)})\n")

        if not delayed:
            print("✅ لا يوجد قرارات متأخرة بهذا المعيار.")
            return

        results = []
        for i, (d, rep, created, exited, gap_h) in enumerate(delayed):
            if i > 0:
                await asyncio.sleep(0.5)
            entry = float(rep.entry_price or 0)
            sl    = float(rep.stop_loss or 0)
            tp1   = float(rep.take_profit_1 or 0)
            tp2   = float(rep.take_profit_2 or tp1)
            is_buy = (rep.signal_type.value if hasattr(rep.signal_type, "value") else rep.signal_type) == "BUY"
            if not (entry and sl and tp1):
                r = {"status": "SKIP_MISSING_LEVELS"}
            else:
                r = await check_decision(rep.market, entry, sl, tp1, tp2, is_buy, created, exited)
            r["decision_id"] = d["id"]
            r["market"] = d["market"]
            r["timeframe"] = d["timeframe"]
            r["user_count"] = d["user_count"]
            r["recorded"] = d["status"]
            r["gap_h"] = gap_h
            results.append(r)

            tag = ""
            if r["status"] == "OK":
                if r["both_touched"]:
                    match = r["real_first"] == r["recorded"]
                    tag = "⚠️ لمست الاثنين!  " + ("✅ متطابق" if match else f"❌ MISMATCH (حقيقي={r['real_first']})")
                else:
                    tag = "✅ لمست مستوى واحد بس"
            print(f"  قرار#{d['id']:5d} {d['market']:10s} {d['timeframe']:4s}  "
                  f"مستخدمون={d['user_count']}  gap={gap_h:.1f}h  [{r['status']}]  {tag}")

        ok_results = [r for r in results if r["status"] == "OK"]
        both = [r for r in ok_results if r["both_touched"]]
        mismatches = [r for r in both if r["real_first"] != r["recorded"]]
        affected_users = sum(r["user_count"] for r in mismatches)

        print("\n" + "="*90)
        print("📊 النتيجة الإجمالية — حجم الخطر الفعلي (بعد تجميع صحيح)")
        print("="*90)
        print(f"  إجمالي القرارات الفريدة المتأخرة: {len(delayed)}")
        print(f"  تحقّقت فعلياً (بيانات متاحة): {len(ok_results)}")
        if ok_results:
            print(f"  لمست SL وTP الاثنين بنفس النافذة: {len(both)}  ({len(both)/len(ok_results)*100:.1f}%)")
        print(f"  قرارات فريدة معكوسة فعلياً (مؤكدة): {len(mismatches)}")
        print(f"  عدد المستخدمين المتأثرين فعلياً (إشعار نتيجة خاطئة): {affected_users}")
        if mismatches:
            print("\n  🚨 القرارات المعكوسة فعلياً:")
            for r in mismatches:
                print(f"     قرار#{r['decision_id']} {r['market']} ({r['timeframe']}) — "
                      f"مستخدمون={r['user_count']}  مسجّل={r['recorded']} لكن الحقيقي={r['real_first']}")

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
