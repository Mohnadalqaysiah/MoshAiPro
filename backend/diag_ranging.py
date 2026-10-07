"""
diag_ranging.py
============================
تحليل قراءة فقط — لماذا طور Wyckoff "RANGING" سالب ومستقر (-0.26R، ن=32
بتقرير الجودة 7 أيام 2026-10-07، بيانات نظيفة بعد التراجع فقط)؟

السياق من قراءة الكود (ict_engine.py + ai_engine_v5.py):
- RANGING تُكتشف لما حركة السعر خلال 20 شمعة < 1.5% وبلا فوليوم مرتفع
  (analyze_wyckoff)، وتُلصق فيها action="WAIT" داخلياً.
- detect_market_mode() تجمع RANGING مع ACCUMULATION/DISTRIBUTION/SIDEWAYS
  بنفس السلّة mode="RANGE" → عتبة قرار أعلى (30 بدل 18 بالاتجاه الرائج).
- السؤال: هل "WAIT" الداخلية هاي يُتجاوَزها فعلياً (إشارة تصدر رغم
  التوصية الداخلية بالانتظار)؟ وهل ai_confidence لإشارات RANGING فعلاً
  أقل، ولا نفس توزيع باقي الإشارات رغم التحذير الداخلي؟

هالسكربت يفحص فقط — بلا أي تعديل:
 1) RANGING مقابل كل الأطوار التانية (الأساس للمقارنة)
 2) تفصيل RANGING: حسب الاتجاه (BUY/SELL) — هل هي فعلياً قصة BUY متخفّية؟
 3) تفصيل RANGING: حسب الرمز — هيمنة رمز واحد ولا موزّعة؟
 4) تفصيل RANGING: حسب فئة الثقة — هل فعلاً أقل من باقي الإشارات؟
 5) متوسط الثقة RANGING مقابل غير-RANGING مباشرة

التشغيل:
  docker cp diag_ranging.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/diag_ranging.py
"""
import sys
sys.path.insert(0, "/app")

from datetime import datetime, timezone
from collections import defaultdict, Counter
from app.database import SessionLocal
from app.models.signal import Signal
from app.services.decision_grouping import verified_unique_decisions

# نفس لحظة إعادة تشغيل الباكند بعد نشر تراجع 1R/2R — المرجع المعتمد
# بـDECISIONS.md لكل فحص "بيانات نظيفة بعد التراجع فقط"
CUTOFF     = datetime(2026, 9, 30, 10, 54, 35, tzinfo=timezone.utc)
CLOSED     = {"TP1_HIT", "TP2_HIT", "SL_HIT"}
MIN_SAMPLE = 15


def conf_bucket(c):
    if c is None:
        return "غير مسجَّلة"
    if c < 55:
        return "< 55%"
    if c < 65:
        return "55-65%"
    if c < 75:
        return "65-75%"
    if c < 85:
        return "75-85%"
    return "85%+"


def stats_line(label, rows):
    n = len(rows)
    if n == 0:
        print(f"  {label:<26} (لا توجد قرارات)")
        return
    wins = sum(1 for d in rows if d["status"] in ("TP1_HIT", "TP2_HIT"))
    pts  = sum(d["points"] for d in rows)
    warn = f"  ⚠️ عينة {n} < {MIN_SAMPLE} — غير قاطعة" if n < MIN_SAMPLE else ""
    print(f"  {label:<26} n={n:>3d}  winrate={wins/n*100:>5.1f}%  نقاط={pts:>+9.2f}  "
          f"exp={pts/n:>+7.2f}{warn}")


def main():
    db = SessionLocal()
    try:
        signals   = db.query(Signal).filter(Signal.created_at >= CUTOFF).all()
        decisions = [d for d in verified_unique_decisions(signals) if d["status"] in CLOSED]
        reps = {s.id: s for s in db.query(Signal).filter(
            Signal.id.in_([d["id"] for d in decisions])).all()}

        ranging, other = [], []
        for d in decisions:
            rep = reps.get(d["id"])
            phase = str(rep.wyckoff_phase) if rep is not None else None
            if phase == "RANGING":
                ranging.append((d, rep))
            else:
                other.append((d, rep))

        print("=" * 104)
        print(f"الأساس — كل القرارات المحسومة منذ {CUTOFF.isoformat()} (بعد التراجع فقط)")
        print("=" * 104)
        stats_line("كل القرارات", decisions)
        stats_line("RANGING فقط", [d for d, _ in ranging])
        stats_line("كل الأطوار الأخرى", [d for d, _ in other])

        print("\n" + "=" * 104)
        print("1) RANGING — حسب الاتجاه (هل هي قصة BUY متخفّية؟)")
        print("=" * 104)
        by_dir = defaultdict(list)
        for d, rep in ranging:
            by_dir[d["signal_type"]].append(d)
        for k in ("BUY", "SELL", "WATCH"):
            if k in by_dir:
                stats_line(k, by_dir[k])

        print("\n" + "=" * 104)
        print("2) RANGING — حسب الرمز (هيمنة رمز واحد ≤60%؟)")
        print("=" * 104)
        mix = Counter(d["market"] for d, _ in ranging)
        total = len(ranging)
        for sym, cnt in mix.most_common(10):
            print(f"  {sym:<12} {cnt:>3d}  ({cnt/total*100:>5.1f}%)")

        print("\n" + "=" * 104)
        print("3) RANGING — حسب فئة الثقة (مقارنة بتوزيع كل الإشارات)")
        print("=" * 104)
        by_conf_ranging = defaultdict(list)
        for d, rep in ranging:
            c = rep.ai_confidence if rep is not None else None
            by_conf_ranging[conf_bucket(c)].append(d)
        for k in ("< 55%", "55-65%", "65-75%", "75-85%", "85%+", "غير مسجَّلة"):
            if k in by_conf_ranging:
                stats_line(k, by_conf_ranging[k])

        print("\n" + "=" * 104)
        print("4) متوسط الثقة (ai_confidence) — RANGING مقابل غير-RANGING")
        print("=" * 104)
        rconf = [rep.ai_confidence for _, rep in ranging if rep is not None and rep.ai_confidence is not None]
        oconf = [rep.ai_confidence for _, rep in other if rep is not None and rep.ai_confidence is not None]
        if rconf:
            print(f"  RANGING       n={len(rconf)}  متوسط={sum(rconf)/len(rconf):.1f}  "
                  f"أدنى={min(rconf):.1f}  أعلى={max(rconf):.1f}")
        if oconf:
            print(f"  غير RANGING   n={len(oconf)}  متوسط={sum(oconf)/len(oconf):.1f}  "
                  f"أدنى={min(oconf):.1f}  أعلى={max(oconf):.1f}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
