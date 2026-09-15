"""
analyze_quality_levers.py
============================
تحليل قراءة فقط — يبحث عن روافع ترفع جودة الإشارات **بلا حذف أي رمز**
(العملاء يريدون الذهب والفضة والنفط والناسداك والفوركس — التغطية مطلوبة،
فالحل يجب أن يكون تصفية أذكى لا تقليص نطاق).

يفحص أربع روافع مخزَّنة فعلاً بجدول signals لكل إشارة:

 1) الجلسة (مشتقّة من created_at UTC): آسيوية / لندن / نيويورك / خارج
    الجلسات. مبدأ ICT الأساسي أن الإعدادات داخل الـkillzones أعلى جودة،
    والمنصة عندها killzones_engine لكنها لا تبني عليه أي بوابة.
    (عمود killzone بالجدول موجود لكنه لا يُملأ عند الإنشاء — فنشتقّه
     من الوقت بدل الاعتماد على حقل فارغ.)

 2) المنطقة × الاتجاه (premium_discount): شراء من Discount وبيع من
    Premium = القاعدة الصحيحة بـICT. الذهب وحده تمنعه Rule 6 من كسرها
    (XAUUSD_BUY_IN_PREMIUM_ZONE / XAUUSD_SELL_IN_DISCOUNT_ZONE)، أما
    بقية الرموز فتُصدر إشارات مخالفة بلا مانع. هذه الرافعة تختبر مباشرة
    هل تعميم قاعدة الذهب على الجميع مبرَّر بالأرقام.

 3) نسبة المخاطرة/العائد المسجّلة وقت الإصدار.

 4) طور Wyckoff.

⚠️ انضباط إلزامي بقراءة النتائج: كل شريحة عيّنتها < 15 تُعلَّم "غير
قاطعة". ولأننا نفحص شرائح كثيرة، بعضها سيبدو جيداً بالصدفة — لذلك
لا تُعتمد أي رافعة إلا إذا تحققت ثلاثة شروط معاً:
   (أ) عيّنة كافية، (ب) فرق winrate واضح، (ج) اتساق عبر أكثر من رمز
       (يُعرض توزيع الرموز بكل شريحة لهذا الغرض تحديداً).
النقاط غير قابلة للمقارنة بين الرموز (مضاعفات _calc_points مختلفة)،
فالمقياس المقارن الأساسي = winrate.

التشغيل:
  docker cp analyze_quality_levers.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/analyze_quality_levers.py
"""
import sys
sys.path.insert(0, "/app")

from datetime import datetime, timezone
from collections import defaultdict, Counter
from app.database import SessionLocal
from app.models.signal import Signal
from app.services.decision_grouping import verified_unique_decisions

CUTOFF     = datetime(2026, 8, 18, tzinfo=timezone.utc)
CLOSED     = {"TP1_HIT", "TP2_HIT", "SL_HIT"}
MIN_SAMPLE = 15


def session_of(dt):
    """جلسة تقريبية بتوقيت UTC (killzones ICT الشائعة)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    h = dt.astimezone(timezone.utc).hour
    if 7 <= h < 12:
        return "لندن (07-12)"
    if 12 <= h < 17:
        return "نيويورك (12-17)"
    if 17 <= h < 23:
        return "مساء/تصريف (17-23)"
    return "آسيوية (23-07)"


def zone_vs_direction(pd_raw, side):
    """هل الإشارة متوافقة مع قاعدة ICT للمناطق؟"""
    if not pd_raw:
        return "غير مسجَّلة"
    raw = str(pd_raw).upper()
    is_prem = "PREMIUM" in raw or "علاوة" in str(pd_raw)
    is_disc = "DISCOUNT" in raw or "خصم" in str(pd_raw)
    if not (is_prem or is_disc):
        return f"أخرى ({pd_raw})"
    if side == "BUY":
        return "شراء من Discount ✅" if is_disc else "شراء من Premium ⚠️"
    return "بيع من Premium ✅" if is_prem else "بيع من Discount ⚠️"


def report(title, buckets, order=None):
    print("\n" + "=" * 104)
    print(title)
    print("=" * 104)
    keys = order or sorted(buckets.keys(), key=lambda k: -len(buckets[k]))
    for k in keys:
        rows = buckets.get(k) or []
        n = len(rows)
        if n == 0:
            print(f"  {k:<26} (لا توجد قرارات)")
            continue
        wins = sum(1 for d in rows if d["status"] in ("TP1_HIT", "TP2_HIT"))
        pts  = sum(d["points"] for d in rows)
        mix  = ", ".join(f"{s}×{c}" for s, c in Counter(d["market"] for d in rows).most_common(4))
        warn = f"  ⚠️ عينة {n} < {MIN_SAMPLE} — غير قاطعة" if n < MIN_SAMPLE else ""
        print(f"  {k:<26} n={n:>3d}  winrate={wins/n*100:>5.1f}%  نقاط={pts:>+9.2f}  "
              f"exp={pts/n:>+7.2f}{warn}")
        print(f"  {'':<26} الرموز: {mix}")


def main():
    db = SessionLocal()
    try:
        signals   = db.query(Signal).filter(Signal.created_at >= CUTOFF).all()
        decisions = [d for d in verified_unique_decisions(signals) if d["status"] in CLOSED]
        reps = {s.id: s for s in db.query(Signal).filter(
            Signal.id.in_([d["id"] for d in decisions])).all()}

        n = len(decisions)
        wins = sum(1 for d in decisions if d["status"] in ("TP1_HIT", "TP2_HIT"))
        pts  = sum(d["points"] for d in decisions)
        print("=" * 104)
        print(f"الأساس للمقارنة — كل القرارات المحسومة منذ {CUTOFF.date()}")
        print("=" * 104)
        print(f"  n={n}  رابح={wins}  winrate={wins/n*100:.1f}%  نقاط={pts:+.2f}  exp={pts/n:+.2f}")

        by_session = defaultdict(list)
        by_zone    = defaultdict(list)
        by_rr      = defaultdict(list)
        by_wyckoff = defaultdict(list)
        raw_zones  = Counter()

        for d in decisions:
            rep = reps.get(d["id"])
            by_session[session_of(d["created_at"])].append(d)

            if rep is not None:
                raw_zones[str(rep.premium_discount)] += 1
                by_zone[zone_vs_direction(rep.premium_discount, d["signal_type"])].append(d)
                by_wyckoff[str(rep.wyckoff_phase or "غير مسجَّل")].append(d)

            rr = d.get("risk_reward_ratio")
            if rr is None:
                by_rr["غير مسجَّلة"].append(d)
            elif rr < 1.3:
                by_rr["RR < 1.3"].append(d)
            elif rr < 1.8:
                by_rr["RR 1.3-1.8"].append(d)
            elif rr < 2.5:
                by_rr["RR 1.8-2.5"].append(d)
            else:
                by_rr["RR ≥ 2.5"].append(d)

        report("1) حسب الجلسة الزمنية (killzones — لا تُستخدم حالياً كبوابة)", by_session,
               order=["آسيوية (23-07)", "لندن (07-12)", "نيويورك (12-17)", "مساء/تصريف (17-23)"])

        report("2) المنطقة × الاتجاه — يختبر مباشرة تعميم قاعدة الذهب (Rule 6) على الجميع", by_zone)
        print(f"\n  القيم الخام المسجَّلة بحقل premium_discount: "
              + ", ".join(f"{k}×{v}" for k, v in raw_zones.most_common(8)))

        report("3) حسب نسبة المخاطرة/العائد وقت الإصدار", by_rr,
               order=["RR < 1.3", "RR 1.3-1.8", "RR 1.8-2.5", "RR ≥ 2.5", "غير مسجَّلة"])

        report("4) حسب طور Wyckoff", by_wyckoff)
    finally:
        db.close()


if __name__ == "__main__":
    main()
