"""
analyze_symbol_timeframe_crosstab.py
=======================================
تحليل قراءة فقط — تقاطع رمز×فريم لتحديد هل سلبية فريم 15m ككل مركّزة
برمز معين (مثلاً XAGUSD) أو موزّعة عبر كل الرموز بالتساوي.

لكل رمز عنده ≥10 قرار على فريم 15m تحديداً: يقارن winrate/expectancy
لصفقاته على 15m مقابل باقي فريماته (15m vs non-15m لنفس الرمز)، منذ
2026-08-18، عبر verified_unique_decisions() المعتادة.

التشغيل:
  docker cp analyze_symbol_timeframe_crosstab.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/analyze_symbol_timeframe_crosstab.py
"""
import sys
sys.path.insert(0, "/app")

from datetime import datetime, timezone
from collections import defaultdict
from app.database import SessionLocal
from app.models.signal import Signal
from app.services.decision_grouping import verified_unique_decisions

CUTOFF = datetime(2026, 8, 18, tzinfo=timezone.utc)
CLOSED = {"TP1_HIT", "TP2_HIT", "SL_HIT"}
MIN_SAMPLE_15M = 10


def stats(rows):
    n = len(rows)
    wins = sum(1 for d in rows if d["status"] in ("TP1_HIT", "TP2_HIT"))
    points = sum(d["points"] for d in rows)
    wr = wins / n * 100 if n else 0
    exp = points / n if n else 0
    return n, wins, wr, points, exp


def main():
    db = SessionLocal()
    try:
        signals = db.query(Signal).filter(Signal.created_at >= CUTOFF).all()
        decisions = verified_unique_decisions(signals)
        closed = [d for d in decisions if d["status"] in CLOSED]
        print(f"📊 قرارات فريدة محسومة منذ {CUTOFF.date()}: {len(closed)}\n")

        by_symbol = defaultdict(list)
        for d in closed:
            by_symbol[d["market"]].append(d)

        print("="*100)
        print(f"{'الرمز':10s}  {'15m: n/winrate/نقاط/exp':38s}  {'باقي الفريمات: n/winrate/نقاط/exp':38s}")
        print("="*100)

        all_symbols = []
        for symbol, rows in by_symbol.items():
            tf15 = [d for d in rows if d["timeframe"] == "15m"]
            rest = [d for d in rows if d["timeframe"] != "15m"]
            if not tf15:
                continue   # هالرمز أصلاً ماله صفقات 15m، لا داعي يظهر بجدول 15m
            n15, w15, wr15, pts15, exp15 = stats(tf15)
            nr, wr_, wrr, ptsr, expr = stats(rest)
            all_symbols.append((symbol, n15, wr15, pts15, exp15, nr, wrr, ptsr, expr))

        all_symbols.sort(key=lambda x: x[3])  # فرز حسب نقاط الـ15m (الأسوأ أولاً) — يوضّح أكبر مساهم بالخسارة

        qualifying = [s for s in all_symbols if s[1] >= MIN_SAMPLE_15M]

        for symbol, n15, wr15, pts15, exp15, nr, wrr, ptsr, expr in all_symbols:
            small = "" if n15 >= MIN_SAMPLE_15M else f"  ⚠️ عينة صغيرة (<{MIN_SAMPLE_15M})"
            rest_str = f"n={nr:3d} wr={wrr:5.1f}% pts={ptsr:+8.2f} exp={expr:+6.3f}" if nr else "لا توجد صفقات على فريم آخر"
            print(f"{symbol:10s}  n={n15:3d} wr={wr15:5.1f}% pts={pts15:+8.2f} exp={exp15:+6.3f}{small}    {rest_str}")

        print(f"\n  (إجمالي رموز عندها أي صفقة 15m: {len(all_symbols)} — منها {len(qualifying)} بعينة ≥{MIN_SAMPLE_15M})")

        if not qualifying:
            print(f"⚠️ لا يوجد أي رمز عنده ≥{MIN_SAMPLE_15M} قرار على فريم 15m — لا يمكن الفصل بثقة برمز واحد لوحده.")
            print("   راجع الجدول فوق لكل الرموز بعيّناتها الصغيرة كمؤشر أولي بس.")
            return

        print("\n" + "="*100)
        print("📊 ملخص")
        print("="*100)
        total_15m_pts = sum(pts15 for _, _, _, pts15, _, _, _, _, _ in qualifying)
        print(f"  إجمالي نقاط 15m لكل الرموز المؤهّلة (n≥{MIN_SAMPLE_15M}): {total_15m_pts:+.2f}")
        worst = qualifying[0]
        print(f"  أضعف رمز على 15m تحديداً: {worst[0]} (expectancy={worst[4]:+.3f}, n={worst[1]})")
        if worst[5] > 0:
            print(f"    → نفس الرمز على باقي الفريمات: expectancy={worst[8]:+.3f} (n={worst[5]}) — "
                  + ("فرق واضح، المشكلة مركّزة بـ15m لهذا الرمز تحديداً" if worst[8] > worst[4] + 1 else "أداء مشابه، المشكلة مش خاصة بـ15m لهذا الرمز"))

    finally:
        db.close()


if __name__ == "__main__":
    main()
