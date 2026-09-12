"""
analyze_strategy_quality.py
==============================
تحليل قراءة فقط بالكامل (لا تعديل، لا كتابة) — يجاوب على أربعة أسئلة
حول جودة القرارات منذ 2026-08-18 (بيانات نظيفة بعد كل تصحيحات اليوم)،
باستخدام verified_unique_decisions() الحيّة كالمعتاد:

  1) الأداء حسب الرمز (winrate، نقاط، لكل رمز عنده ≥5 قرارات)
  2) الأداء حسب الفريم الزمني (winrate، نقاط، expectancy/قرار)
  3) محاكاة "هدف أقرب" — TP1 بنصف المسافة الحالية، تحقق فعلي من بيانات
     OHLC حقيقية شمعة-شمعة (هل كانت تصل قبل الستوب؟)
  4) معايرة الثقة — هل ai_confidence المسجّل وقت القرار يطابق فعلياً
     نسبة النجاح الحقيقية، مقسّمة لفئات

⚠️ ملاحظة صادقة على النطاق: طُلب أيضاً تجربة "أقرب Order Block/FVG"
كهدف بديل — فحصت الكود ولقيت الحقول المخصصة لهذا بجدول signals
(liquidity_analysis, bos_analysis, volume_analysis) غير مُعبّأة
إطلاقاً وقت إنشاء أي إشارة (لا يوجد أي كود يكتب فيها) — يعني ما في
سجل تاريخي لمواقع الـOB/FVG وقت كل قرار. تنفيذ هذا فعلياً يحتاج
إعادة تشغيل محرك التحليل الهيكلي الكامل ICT/SMC على كل شمعة تاريخية
لإعادة اشتقاق المناطق رجعياً — مجهود أكبر بكثير من نطاق سكربت تشخيصي،
وناتجه غير مضمون التطابق مع ما كان "حياً" وقتها. اكتفيت بمحاكاة
"نصف المسافة" فقط، وأنبّه هون صراحة إنه القسم الثاني (OB/FVG) لم
يُنفَّذ لهذا السبب — قرار موثّق، مش إغفال.

التشغيل:
  docker cp analyze_strategy_quality.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/analyze_strategy_quality.py 2>/dev/null
"""
import sys, asyncio
sys.path.insert(0, "/app")

from datetime import datetime, timezone
from collections import defaultdict
from app.database import SessionLocal
from app.models.signal import Signal
from app.services.smart_data import smart_data
from app.services.decision_grouping import verified_unique_decisions

CUTOFF = datetime(2026, 8, 18, tzinfo=timezone.utc)
CLOSED = {"TP1_HIT", "TP2_HIT", "SL_HIT"}
MIN_SAMPLE = 15   # تحذير صريح تحت هذا الرقم
MIN_SYMBOL_SAMPLE = 5


def summarize(rows, label_fn):
    """rows: list of decision dicts. يرجّع dict[label] -> {n, wins, losses, points}"""
    buckets = defaultdict(lambda: {"n": 0, "wins": 0, "losses": 0, "points": 0.0})
    for d in rows:
        label = label_fn(d)
        b = buckets[label]
        b["n"] += 1
        if d["status"] in ("TP1_HIT", "TP2_HIT"):
            b["wins"] += 1
        else:
            b["losses"] += 1
        b["points"] += d["points"]
    return buckets


def print_table(buckets, title, min_sample):
    print(f"\n{'='*90}\n{title}\n{'='*90}")
    rows = sorted(buckets.items(), key=lambda kv: (kv[1]["wins"] / kv[1]["n"] if kv[1]["n"] else 0))
    for label, b in rows:
        wr = b["wins"] / b["n"] * 100 if b["n"] else 0
        exp = b["points"] / b["n"] if b["n"] else 0
        warn = "  ⚠️ عينة صغيرة (<%d) — لا استنتاج قاطع" % min_sample if b["n"] < min_sample else ""
        print(f"  {label:12s}  n={b['n']:4d}  winrate={wr:5.1f}%  نقاط={b['points']:+9.2f}  "
              f"expectancy/قرار={exp:+7.3f}{warn}")


async def simulate_closer_tp(decisions, rep_rows):
    """محاكاة: لو TP1 كان بنصف المسافة الحالية، هل كانت تصل قبل الستوب؟"""
    results = []
    for i, d in enumerate(decisions):
        if i > 0:
            await asyncio.sleep(0.4)
        rep = rep_rows.get(d["id"])
        if not rep or not rep.entry_price or not rep.stop_loss or not rep.take_profit_1:
            continue
        entry = float(rep.entry_price)
        sl    = float(rep.stop_loss)
        tp1   = float(rep.take_profit_1)
        is_buy = (rep.signal_type.value if hasattr(rep.signal_type, "value") else rep.signal_type) == "BUY"
        tp1_half = entry + (tp1 - entry) / 2

        created = rep.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        hours_since = (now - created).total_seconds() / 3600
        bars_needed = max(30, int(hours_since) + 10)

        try:
            df = await smart_data.get_ohlcv(rep.market, "1h", bars=bars_needed)
        except Exception:
            continue
        if df is None or df.empty:
            continue

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
            continue

        sim_result = None
        for ts, hi, lo in rows:
            hi, lo = float(hi), float(lo)
            sl_touch = (lo <= sl) if is_buy else (hi >= sl)
            tp_touch = (hi >= tp1_half) if is_buy else (lo <= tp1_half)
            if sl_touch:
                sim_result = "SL_HIT"; break
            if tp_touch:
                sim_result = "TP1_HIT"; break
        if sim_result is None:
            continue

        results.append({
            "id": d["id"], "market": d["market"], "actual": d["status"],
            "actual_points": d["points"], "sim": sim_result,
        })
    return results


async def main():
    db = SessionLocal()
    try:
        signals = db.query(Signal).filter(Signal.created_at >= CUTOFF).all()
        decisions = verified_unique_decisions(signals)
        closed = [d for d in decisions if d["status"] in CLOSED]
        print(f"📊 قرارات فريدة محسومة منذ {CUTOFF.date()}: {len(closed)}")

        # ── 1) حسب الرمز ─────────────────────────────────────────────────
        by_symbol = summarize(closed, lambda d: d["market"])
        by_symbol = {k: v for k, v in by_symbol.items() if v["n"] >= MIN_SYMBOL_SAMPLE}
        print_table(by_symbol, "1) الأداء حسب الرمز (≥5 قرارات)", MIN_SAMPLE)

        # تجميع فئة "كريبتو صغير"
        small_crypto = {"ADAUSD", "SOLUSD", "DOGEUSD", "XRPUSD"}
        sc_rows = [d for d in closed if d["market"] in small_crypto]
        if sc_rows:
            b = summarize(sc_rows, lambda d: "small_crypto")["small_crypto"]
            wr = b["wins"] / b["n"] * 100
            print(f"\n  فئة الكريبتو الصغير مجمّعة (ADA/SOL/DOGE/XRP): n={b['n']}  "
                  f"winrate={wr:.1f}%  نقاط={b['points']:+.2f}")

        # ── 2) حسب الفريم ────────────────────────────────────────────────
        by_tf = summarize(closed, lambda d: d["timeframe"])
        print_table(by_tf, "2) الأداء حسب الفريم الزمني", MIN_SAMPLE)

        # ── 4) معايرة الثقة ──────────────────────────────────────────────
        def conf_bucket(d):
            c = d.get("ai_confidence") or 0
            if c < 60: return "under_60"
            if c < 65: return "60-65"
            if c < 75: return "65-75"
            return "75+"
        by_conf = summarize(closed, conf_bucket)
        print_table(by_conf, "4) معايرة الثقة (ai_confidence وقت القرار مقابل النتيجة الفعلية)", MIN_SAMPLE)

        # ── 3) محاكاة هدف أقرب (OHLC حقيقي) ──────────────────────────────
        rep_ids = [d["id"] for d in closed]
        rep_rows = {s.id: s for s in db.query(Signal).filter(Signal.id.in_(rep_ids)).all()}
        print(f"\n{'='*90}\n3) محاكاة TP1 بنصف المسافة الحالية (تحقق OHLC حقيقي، قد يستغرق دقائق)\n{'='*90}")
        sim_results = await simulate_closer_tp(closed, rep_rows)
        n = len(sim_results)
        print(f"  قرارات أمكن محاكاتها: {n} من أصل {len(closed)}")
        if n:
            sim_wins = sum(1 for r in sim_results if r["sim"] == "TP1_HIT")
            sim_wr = sim_wins / n * 100
            actual_wins = sum(1 for r in sim_results if r["actual"] in ("TP1_HIT", "TP2_HIT"))
            actual_wr = actual_wins / n * 100
            # نقاط تقريبية: افترض نفس مقياس points الحالي متناسب مع نصف المسافة تقريباً
            flips_to_win  = sum(1 for r in sim_results if r["sim"] == "TP1_HIT" and r["actual"] == "SL_HIT")
            flips_to_loss = sum(1 for r in sim_results if r["sim"] == "SL_HIT" and r["actual"] in ("TP1_HIT", "TP2_HIT"))
            print(f"  winrate الفعلي (نفس العينة): {actual_wr:.1f}%  ({actual_wins}/{n})")
            print(f"  winrate المحاكى (هدف أنصف): {sim_wr:.1f}%  ({sim_wins}/{n})")
            print(f"  قرارات كانت SL_HIT فعلياً لكن كانت ستربح بهدف أقرب: {flips_to_win}")
            print(f"  قرارات كانت رابحة فعلياً لكن كانت ستخسر بهدف أقرب (SL أسرع من نصف الهدف): {flips_to_loss}")
            if n < MIN_SAMPLE:
                print(f"  ⚠️ عينة صغيرة (<{MIN_SAMPLE}) — مؤشر أولي فقط.")

        print(f"\n{'='*90}\nملخص وترتيب أولويات (بناءً على الأرقام فوق فقط)\n{'='*90}")
        print("  راجع الجداول يدوياً — الترتيب النهائي يعتمد على أي فئة عندها")
        print("  عينة كافية (≥15) وفرق winrate واضح (>10 نقطة مئوية) عن المتوسط العام.")

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
