"""
analyze_levers_confound.py
=============================
تحليل قراءة فقط — يختبر هل الرافعتان الواعدتان حقيقيتان أم التباس
تركيبة رموز، قبل بناء أي بوابة عليهما.

النتيجة الخام (162 قرار) أظهرت:
  • الجلسة الآسيوية (n=41): -633.19 نقطة، exp -15.44 — الجلسة السالبة
    الوحيدة. لكن تركيبتها XAGUSD×11 + SOLUSD×5 + BNBUSD×3 + XRPUSD×2،
    وهذه رموز تتداول 24 ساعة ومرصودة ضعيفة أصلاً بتحليل مستقل — أي أن
    "الآسيوية سيئة" قد تكون فقط "الكريبتو والفضة سيئان، وهما من يتداول
    ليلاً".
  • RR 1.8-2.5 (n=61): 21.3% winrate و-447.41 نقطة، مقابل RR 1.3-1.8
    (n=48): 33.3% و+883.97 — أي أن RR الأعلى أسوأ. يتوافق مع نتيجة
    سابقة مستقلة (محاكاة تشديد min_rr خفضت expectancy بدل رفعها)، لكن
    تركيبة الشرائح مختلفة أيضاً.

الاختبار: إعادة حساب الرافعتين على خمس مجموعات مختلفة. النمط الحقيقي
يصمد عبرها؛ ونمط الالتباس ينهار عند إزالة الرموز المسيطرة.

⚠️ النقاط غير قابلة للمقارنة بين الرموز (مضاعفات _calc_points مختلفة:
فوركس ×10000، كريبتو نسبة مئوية، معادن ×10، أسهم خليجية مختلفة تماماً)
— فالمقياس المقارن المعتمد هنا هو winrate، والنقاط تُعرض للسياق فقط.

التشغيل:
  docker cp analyze_levers_confound.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/analyze_levers_confound.py
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

SMALL_CRYPTO = {"SOLUSD", "ADAUSD", "BNBUSD", "XRPUSD", "DOGEUSD"}
GULF = {"ALINMA", "QNBK", "SNB", "RAJHI", "MAADEN", "ALMARAI", "BAHRI", "SABIC",
        "ARAMCO", "EMAAR", "DIB", "ADNOCDIST", "EMIRATESNBD"}
# ما يهم العميل فعلاً حسب الطلب الصريح: الذهب والبتكوين أولوية قصوى،
# ومعهم الناسداك والفضة والنفط والفوركس.
PRIORITY = {"XAUUSD", "BTCUSD", "ETHUSD", "XAGUSD", "XPTUSD", "COPPER",
            "NAS100", "US30", "SP500", "USOIL", "NATGAS",
            "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD",
            "NZDUSD", "EURGBP", "EURJPY", "GBPJPY", "DXY"}

SESSIONS = ["آسيوية (23-07)", "لندن (07-12)", "نيويورك (12-17)", "مساء (17-23)"]
RR_BUCKETS = ["RR < 1.3", "RR 1.3-1.8", "RR 1.8-2.5", "RR ≥ 2.5"]


def session_of(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    h = dt.astimezone(timezone.utc).hour
    if 7 <= h < 12:   return SESSIONS[1]
    if 12 <= h < 17:  return SESSIONS[2]
    if 17 <= h < 23:  return SESSIONS[3]
    return SESSIONS[0]


def rr_of(d):
    rr = d.get("risk_reward_ratio")
    if rr is None:            return "غير مسجَّلة"
    if rr < 1.3:              return RR_BUCKETS[0]
    if rr < 1.8:              return RR_BUCKETS[1]
    if rr < 2.5:              return RR_BUCKETS[2]
    return RR_BUCKETS[3]


def stat(rows):
    n = len(rows)
    if not n:
        return None
    wins = sum(1 for d in rows if d["status"] in ("TP1_HIT", "TP2_HIT"))
    pts  = sum(d["points"] for d in rows)
    return n, wins / n * 100, pts


def show(title, decisions, keyfn, order):
    print(f"\n  ── {title} (n={len(decisions)}) ──")
    if not decisions:
        print("     لا توجد قرارات.")
        return
    groups = defaultdict(list)
    for d in decisions:
        groups[keyfn(d)].append(d)
    for k in order:
        s = stat(groups.get(k, []))
        if s is None:
            print(f"     {k:<20} —")
            continue
        n, wr, pts = s
        flag = "  ⚠️ غير قاطعة" if n < MIN_SAMPLE else ""
        print(f"     {k:<20} n={n:>3d}  winrate={wr:>5.1f}%  نقاط={pts:>+9.2f}{flag}")


def main():
    db = SessionLocal()
    try:
        signals   = db.query(Signal).filter(Signal.created_at >= CUTOFF).all()
        decisions = [d for d in verified_unique_decisions(signals) if d["status"] in CLOSED]

        populations = [
            ("كل الرموز (الأساس)",              decisions),
            ("بدون الكريبتو الصغير",            [d for d in decisions if d["market"] not in SMALL_CRYPTO]),
            ("بدون XAGUSD",                     [d for d in decisions if d["market"] != "XAGUSD"]),
            ("بدون الكريبتو الصغير وXAGUSD",    [d for d in decisions if d["market"] not in SMALL_CRYPTO | {"XAGUSD"}]),
            ("رموز الأولوية فقط",               [d for d in decisions if d["market"] in PRIORITY]),
            ("بدون الأسهم الخليجية",            [d for d in decisions if d["market"] not in GULF]),
        ]

        print("=" * 100)
        print("الرافعة 1: الجلسة الزمنية — هل تصمد عبر المجموعات؟")
        print("=" * 100)
        for label, pop in populations:
            show(label, pop, lambda d: session_of(d["created_at"]), SESSIONS)

        print("\n" + "=" * 100)
        print("الرافعة 2: نسبة المخاطرة/العائد — هل تصمد عبر المجموعات؟")
        print("=" * 100)
        for label, pop in populations:
            show(label, pop, rr_of, RR_BUCKETS)

        # ── داخل الرمز الواحد: أقوى عزل للالتباس ─────────────────────────
        print("\n" + "=" * 100)
        print("داخل الرمز الواحد — يعزل أثر الرمز تماماً (الرموز ذات ≥8 قرارات)")
        print("=" * 100)
        by_sym = defaultdict(list)
        for d in decisions:
            by_sym[d["market"]].append(d)
        for sym, rows in sorted(by_sym.items(), key=lambda kv: -len(kv[1])):
            if len(rows) < 8:
                continue
            print(f"\n  {sym} (n={len(rows)}):")
            asian = [d for d in rows if session_of(d["created_at"]) == SESSIONS[0]]
            other = [d for d in rows if session_of(d["created_at"]) != SESSIONS[0]]
            for lbl, grp in (("آسيوية", asian), ("بقية الجلسات", other)):
                s = stat(grp)
                if s is None:
                    print(f"     {lbl:<14} —")
                    continue
                n, wr, pts = s
                print(f"     {lbl:<14} n={n:>3d}  winrate={wr:>5.1f}%  نقاط={pts:>+9.2f}"
                      + ("  ⚠️ غير قاطعة" if n < MIN_SAMPLE else ""))

        low  = [d for d in decisions if rr_of(d) == RR_BUCKETS[1]]
        high = [d for d in decisions if rr_of(d) == RR_BUCKETS[2]]
        print("\n" + "-" * 100)
        print("  تركيبة الشريحتين محل المقارنة بالرافعة 2:")
        print(f"    RR 1.3-1.8: " + ", ".join(f"{s}×{c}" for s, c in Counter(d['market'] for d in low).most_common(6)))
        print(f"    RR 1.8-2.5: " + ", ".join(f"{s}×{c}" for s, c in Counter(d['market'] for d in high).most_common(6)))
    finally:
        db.close()


if __name__ == "__main__":
    main()
