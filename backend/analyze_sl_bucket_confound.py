"""
analyze_sl_bucket_confound.py
================================
تحليل قراءة فقط — يفصل التباساً حرجاً ظهر بنتيجة analyze_sl_distance_quality:

شريحة وقف 0.25-0.50% طلعت الأسوأ (n=74، winrate 21.6%، -377.69 نقطة)
وشريحة 0.50-1.00% الأفضل (n=30، winrate 40.0%، +1349.55). لكن الشريحتين
مختلفتَي التركيبة: الأولى SOLUSD/XRPUSD ثقيلة (كريبتو صغير — فئة سبق
أن رصدناها ضعيفة بحد ذاتها)، والثانية XAGUSD/NATGAS.

السؤال: هل المشكلة مسافة الوقف فعلاً، أم إننا نعيد اكتشاف ضعف الكريبتو
الصغير بمسمّى جديد؟ (نفس درس تقاطع 15m: الإجمالي بدا قاطعاً لحد ما
كشف التوزيع إنه مدفوع بحفنة صفقات شاذة صغيرة العيّنة.)

يجيب بطريقتين مستقلتين:
  1) تقاطع فئة × شريحة وقف — هل النمط موجود بكل الفئات أم بواحدة؟
  2) مقارنة داخل الرمز الواحد (أقوى دليل): نفس الرمز، أوقاف مختلفة —
     يعزل أثر مسافة الوقف عن أثر الرمز تماماً.

كل خلية عيّنتها < 10 تُعلَّم "غير قاطعة" ولا تُحذف. النقاط تُعرض لكن
المقياس المقارن الأساسي = winrate (النقاط غير قابلة للمقارنة بين
الرموز بسبب اختلاف مضاعفات _calc_points).

التشغيل:
  docker cp analyze_sl_bucket_confound.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/analyze_sl_bucket_confound.py
"""
import sys
sys.path.insert(0, "/app")

from datetime import datetime, timezone
from collections import defaultdict
from app.database import SessionLocal
from app.models.signal import Signal
from app.services.decision_grouping import verified_unique_decisions

CUTOFF     = datetime(2026, 8, 18, tzinfo=timezone.utc)
CLOSED     = {"TP1_HIT", "TP2_HIT", "SL_HIT"}
MIN_CELL   = 10   # تحت هذا الرقم: تُعرض معلَّمة، لا تُحذف

BUCKETS = [
    (0.0000, 0.0010, "<0.10%"),
    (0.0010, 0.0025, "0.10-0.25%"),
    (0.0025, 0.0050, "0.25-0.50%"),
    (0.0050, 0.0100, "0.50-1.00%"),
    (0.0100, 9.9999, ">1.00%"),
]

CATEGORIES = {
    "كريبتو صغير": {"ADAUSD", "SOLUSD", "DOGEUSD", "XRPUSD", "BNBUSD"},
    "كريبتو كبير": {"BTCUSD", "ETHUSD"},
    "معادن":       {"XAUUSD", "XAGUSD", "XPTUSD", "COPPER"},
    "فوركس":       {"EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD",
                    "NZDUSD", "EURGBP", "EURJPY", "GBPJPY", "DXY"},
    "طاقة":        {"USOIL", "BRENT", "NATGAS"},
    "مؤشرات":      {"NAS100", "US30", "SP500"},
}


def category_of(sym):
    for name, members in CATEGORIES.items():
        if sym in members:
            return name
    return "أسهم/خليج"


def bucket_of(sl_pct):
    for lo, hi, label in BUCKETS:
        if lo <= sl_pct < hi:
            return label
    return BUCKETS[-1][2]


def cell(rows):
    n = len(rows)
    if not n:
        return None
    wins = sum(1 for r in rows if r["status"] in ("TP1_HIT", "TP2_HIT"))
    pts  = sum(r["points"] for r in rows)
    return {"n": n, "wr": wins / n * 100, "pts": pts, "exp": pts / n}


def fmt(c):
    if c is None:
        return f"{'—':>22s}"
    flag = "*" if c["n"] < MIN_CELL else " "
    return f"{c['n']:>3d}{flag} {c['wr']:>5.1f}% {c['exp']:>+9.2f}    "


def main():
    db = SessionLocal()
    try:
        signals   = db.query(Signal).filter(Signal.created_at >= CUTOFF).all()
        decisions = [d for d in verified_unique_decisions(signals) if d["status"] in CLOSED]
        reps = {s.id: s for s in db.query(Signal).filter(
            Signal.id.in_([d["id"] for d in decisions])).all()}

        enriched = []
        for d in decisions:
            rep = reps.get(d["id"])
            if not rep or not rep.entry_price or not rep.stop_loss:
                continue
            entry, sl = float(rep.entry_price), float(rep.stop_loss)
            if entry <= 0:
                continue
            r = dict(d)
            r["bucket"] = bucket_of(abs(entry - sl) / entry)
            r["cat"]    = category_of(d["market"])
            enriched.append(r)

        labels = [b[2] for b in BUCKETS]
        print(f"قرارات فريدة محسومة: {len(enriched)}   (منذ {CUTOFF.date()})")
        print("كل خلية: n / winrate / expectancy — النجمة (*) تعني عيّنة < %d، غير قاطعة\n" % MIN_CELL)

        # ── 1) فئة × شريحة ───────────────────────────────────────────────
        print("=" * 130)
        print("1) تقاطع الفئة × شريحة الوقف — هل النمط عام أم محصور بفئة؟")
        print("=" * 130)
        header = f"{'الفئة':14s}" + "".join(f"{lab:>22s}" for lab in labels)
        print(header)
        print("-" * 130)
        by_cat = defaultdict(list)
        for r in enriched:
            by_cat[r["cat"]].append(r)
        for cat, rows in sorted(by_cat.items(), key=lambda kv: -len(kv[1])):
            line = f"{cat:14s}"
            for lab in labels:
                line += fmt(cell([r for r in rows if r["bucket"] == lab]))
            print(line + f"   (إجمالي {len(rows)})")

        # ── 2) داخل الرمز الواحد ─────────────────────────────────────────
        print("\n" + "=" * 130)
        print("2) داخل الرمز الواحد — نفس الرمز بأوقاف مختلفة (أقوى دليل: يعزل أثر الرمز)")
        print("=" * 130)
        by_sym = defaultdict(list)
        for r in enriched:
            by_sym[r["market"]].append(r)
        print(f"{'الرمز':12s}" + "".join(f"{lab:>22s}" for lab in labels))
        print("-" * 130)
        for sym, rows in sorted(by_sym.items(), key=lambda kv: -len(kv[1])):
            buckets_present = sum(1 for lab in labels if any(r["bucket"] == lab for r in rows))
            if len(rows) < 6 and buckets_present < 2:
                continue   # لا يضيف شيئاً للمقارنة الداخلية — يظهر بالملخص تحت
            line = f"{sym:12s}"
            for lab in labels:
                line += fmt(cell([r for r in rows if r["bucket"] == lab]))
            print(line + f"   (إجمالي {len(rows)})")

        hidden = [s for s, rows in by_sym.items()
                  if len(rows) < 6 and sum(1 for lab in labels if any(r["bucket"] == lab for r in rows)) < 2]
        if hidden:
            print(f"\n  رموز بصف واحد فقط وعيّنة <6 (لا تصلح لمقارنة داخلية، مذكورة للشفافية): "
                  + ", ".join(f"{s}({len(by_sym[s])})" for s in sorted(hidden)))
    finally:
        db.close()


if __name__ == "__main__":
    main()
