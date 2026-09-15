"""
analyze_sl_distance_quality.py
=================================
تحليل قراءة فقط (لا تعديل إطلاقاً) — يختبر فرضية واحدة محددة:
هل الصفقات ذات وقف الخسارة الضيق جداً هي محرّك رئيسي للخسائر؟

الدافع (بيانات حقيقية من تقرير 15/09): صفقات زي #2438 EURGBP بدخول
0.85556 ووقف 0.85545 = مسافة 1.1 نقطة فقط (السبريد لحاله يضربها)،
و#2408 BNBUSD بوقف 0.07% — هذي أوقاف داخل نطاق الضجيج، مش بنية سوق.

⚠️ الفرضية تُختبر، لا تُفترض: سبق بهالمشروع إن حدس "واضح" (تشديد
min_rr) طلع خاطئ بالأرقام — قلّل expectancy بدل ما يزيدها. ممكن يطلع
إن الأوقاف الضيقة أفضل فعلاً (وقف أصغر = خسارة أصغر بالنقاط)، فالسكربت
يعرض النتيجة كما هي بالاتجاهين.

⚠️ تحذير منهجي مهم بقراءة الجدول: النقاط غير قابلة للمقارنة المباشرة
بين الرموز (مضاعفات مختلفة: فوركس ×10000، كريبتو نسبة مئوية، معادن
×10 — راجع _calc_points). لذلك:
  - المقياس الأساسي القابل للمقارنة = winrate + متوسط R/R
  - النقاط تُعرض كمؤشر ثانوي مع توزيع الرموز بكل شريحة لكشف أي انحياز
كل شريحة عيّنتها < 15 تُعلَّم صراحة "غير قاطعة" (ولا تُحذف — تظهر مع
التحذير، نفس قاعدة بقية تحليلات هالمشروع).

التشغيل:
  docker cp analyze_sl_distance_quality.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/analyze_sl_distance_quality.py
"""
import sys
sys.path.insert(0, "/app")

from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter
from app.database import SessionLocal
from app.models.signal import Signal
from app.services.decision_grouping import verified_unique_decisions

CUTOFF     = datetime(2026, 8, 18, tzinfo=timezone.utc)
CLOSED     = {"TP1_HIT", "TP2_HIT", "SL_HIT"}
MIN_SAMPLE = 15
EXTREME_SL_PCT = 0.001   # 0.1% — يُعرض كل قرار تحته فردياً بالتفصيل

# حدود الشرائح (نسبة مسافة SL من سعر الدخول)
BUCKETS = [
    (0.0000, 0.0010, "< 0.10%  (ضجيج)"),
    (0.0010, 0.0025, "0.10-0.25%"),
    (0.0025, 0.0050, "0.25-0.50%"),
    (0.0050, 0.0100, "0.50-1.00%"),
    (0.0100, 0.0200, "1.00-2.00%"),
    (0.0200, 9.9999, "> 2.00%"),
]


def bucket_of(sl_pct):
    for lo, hi, label in BUCKETS:
        if lo <= sl_pct < hi:
            return label
    return BUCKETS[-1][2]


def report(decisions, rep_rows, title):
    print("\n" + "=" * 104)
    print(title)
    print("=" * 104)

    groups = defaultdict(list)
    extremes = []
    skipped_no_levels = 0

    for d in decisions:
        rep = rep_rows.get(d["id"])
        if not rep or not rep.entry_price or not rep.stop_loss:
            skipped_no_levels += 1
            continue
        entry = float(rep.entry_price)
        sl    = float(rep.stop_loss)
        if entry <= 0:
            skipped_no_levels += 1
            continue
        sl_pct = abs(entry - sl) / entry
        rec = dict(d)
        rec["sl_pct"] = sl_pct
        groups[bucket_of(sl_pct)].append(rec)
        if sl_pct < EXTREME_SL_PCT:
            extremes.append(rec)

    total = sum(len(v) for v in groups.values())
    print(f"قرارات فريدة محسومة بالعيّنة: {total}"
          + (f"   (مستبعدة لعدم وجود مستويات: {skipped_no_levels})" if skipped_no_levels else ""))
    if not total:
        return

    print(f"\n{'الشريحة':22s} {'n':>4s} {'winrate':>8s} {'نقاط':>11s} {'exp/قرار':>10s} {'متوسط RR':>9s}  الرموز الأكثر")
    print("-" * 104)

    for _lo, _hi, label in BUCKETS:
        rows = groups.get(label, [])
        n = len(rows)
        if n == 0:
            print(f"{label:22s} {0:>4d}    —          —          —         —       (لا توجد قرارات)")
            continue
        wins   = sum(1 for r in rows if r["status"] in ("TP1_HIT", "TP2_HIT"))
        points = sum(r["points"] for r in rows)
        rrs    = [float(r["risk_reward_ratio"]) for r in rows if r.get("risk_reward_ratio")]
        avg_rr = sum(rrs) / len(rrs) if rrs else 0.0
        mix    = ", ".join(f"{s}×{c}" for s, c in Counter(r["market"] for r in rows).most_common(3))
        warn   = "  ⚠️ عينة صغيرة (<%d) — غير قاطعة" % MIN_SAMPLE if n < MIN_SAMPLE else ""
        print(f"{label:22s} {n:>4d} {wins/n*100:>7.1f}% {points:>+11.2f} {points/n:>+10.3f} {avg_rr:>9.2f}  {mix}{warn}")

    # ── الحالات المتطرفة، فردياً (تُعرض ولا تُخفى) ──────────────────────
    print("\n" + "-" * 104)
    print(f"القرارات ذات وقف أضيق من {EXTREME_SL_PCT*100:.2f}% — معروضة فردياً ({len(extremes)})")
    print("-" * 104)
    if not extremes:
        print("  لا توجد.")
    else:
        extremes.sort(key=lambda r: r["sl_pct"])
        for r in extremes:
            rep = rep_rows[r["id"]]
            print(f"  #{r['id']:5d} {r['market']:10s} {r['timeframe']:4s} {r['signal_type']:4s} "
                  f"وقف={r['sl_pct']*100:6.4f}%  دخول={rep.entry_price}  SL={rep.stop_loss}  "
                  f"{r['status']:8s} نقاط={r['points']:+8.2f}  {r['created_at']}")


def main():
    db = SessionLocal()
    try:
        signals   = db.query(Signal).filter(Signal.created_at >= CUTOFF).all()
        decisions = [d for d in verified_unique_decisions(signals) if d["status"] in CLOSED]
        rep_rows  = {s.id: s for s in db.query(Signal).filter(
            Signal.id.in_([d["id"] for d in decisions])).all()} if decisions else {}

        report(decisions, rep_rows, f"الفترة الكاملة — منذ {CUTOFF.date()}")

        week_cut = datetime.now(timezone.utc) - timedelta(days=7)
        recent = [d for d in decisions
                  if (d["created_at"].replace(tzinfo=timezone.utc)
                      if d["created_at"].tzinfo is None else d["created_at"]) >= week_cut]
        report(recent, rep_rows, "آخر 7 أيام فقط (هل النمط حديث؟)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
