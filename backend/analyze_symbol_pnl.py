"""
analyze_symbol_pnl.py
========================
تحليل قراءة فقط — أرقام نظيفة لكل رمز، سطر واحد لكل رمز بلا أي جداول
متعددة الأعمدة.

سبب وجوده: جدول analyze_sl_bucket_confound "داخل الرمز الواحد" أعمدته
غير محاذية (دالة التنسيق ترجع 22 محرفاً للخلية الفارغة و25 للممتلئة)،
فقراءة أي رقم مقابل شريحته غير موثوقة — اكتُشف لما جمع SOLUSD أعطى 11
صفقة بينما السطر يقول 13. أي قرار حذف رمز مبني على ذلك الجدول كان
سيكون مبنياً على قراءة مشوّهة.

هنا: رمز واحد لكل سطر، وأرقام مجمَّعة مباشرة بلا ضرب بـexpectancy
مقرَّب (وهو مصدر خطأ تراكمي آخر).

يعرض أيضاً محاكاة صريحة: ماذا تصبح أرقام المنصة لو استُبعدت مجموعة
رموز محددة من الماسح التلقائي.

التشغيل:
  docker cp analyze_symbol_pnl.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/analyze_symbol_pnl.py
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
MIN_SAMPLE = 15

# مرشّحو الاستبعاد من الماسح التلقائي (market_scanner.SCAN_SYMBOLS)
CANDIDATES = ["XAGUSD", "SOLUSD", "ADAUSD", "BNBUSD", "DOGEUSD", "XRPUSD"]


def agg(rows):
    n     = len(rows)
    wins  = sum(1 for d in rows if d["status"] in ("TP1_HIT", "TP2_HIT"))
    pts   = sum(d["points"] for d in rows)
    return n, wins, pts


def line(label, rows, width=14):
    n, wins, pts = agg(rows)
    wr  = wins / n * 100 if n else 0.0
    exp = pts / n if n else 0.0
    flag = "" if n >= MIN_SAMPLE else f"  ⚠️ عينة {n} < {MIN_SAMPLE}"
    return (f"  {label:<{width}} n={n:>3d}  رابح={wins:>3d}  winrate={wr:>5.1f}%  "
            f"نقاط={pts:>+9.2f}  exp={exp:>+8.2f}{flag}")


def main():
    db = SessionLocal()
    try:
        signals   = db.query(Signal).filter(Signal.created_at >= CUTOFF).all()
        decisions = [d for d in verified_unique_decisions(signals) if d["status"] in CLOSED]

        by_sym = defaultdict(list)
        for d in decisions:
            by_sym[d["market"]].append(d)

        n_all, w_all, p_all = agg(decisions)
        print("=" * 92)
        print(f"إجمالي المنصة منذ {CUTOFF.date()}")
        print("=" * 92)
        print(line("الكل", decisions))

        print("\n" + "=" * 92)
        print("كل رمز على حدة — مرتّب بالأسوأ نقاطاً أولاً (بلا حذف أي رمز)")
        print("=" * 92)
        for sym, rows in sorted(by_sym.items(), key=lambda kv: agg(kv[1])[2]):
            print(line(sym, rows, width=12))

        print("\n" + "=" * 92)
        print("محاكاة الاستبعاد — ماذا لو خرج كل مرشّح وحده من الماسح؟")
        print("=" * 92)
        print("  (الأثر الفردي: الفرق الذي يُحدثه استبعاد هذا الرمز وحده)")
        for sym in CANDIDATES:
            rows = by_sym.get(sym, [])
            if not rows:
                print(f"  {sym:<12} لا توجد قرارات محسومة بالفترة")
                continue
            kept = [d for d in decisions if d["market"] != sym]
            kn, kw, kp = agg(kept)
            print(f"  بدون {sym:<8} → n={kn:>3d}  winrate={kw/kn*100:>5.1f}%  نقاط={kp:>+9.2f}"
                  f"   (الفرق: {kp - p_all:>+8.2f} نقطة، {kw/kn*100 - w_all/n_all*100:>+5.2f} نقطة مئوية)")

        print("\n" + "-" * 92)
        print("  استبعاد المجموعة كاملة معاً:")
        kept = [d for d in decisions if d["market"] not in CANDIDATES]
        kn, kw, kp = agg(kept)
        if kn:
            print(f"  بدون {', '.join(CANDIDATES)}")
            print(f"  → n={kn}  رابح={kw}  winrate={kw/kn*100:.1f}%  نقاط={kp:+.2f}  exp={kp/kn:+.2f}")
            print(f"  → الفرق عن الوضع الحالي: {kp - p_all:+.2f} نقطة، "
                  f"{kw/kn*100 - w_all/n_all*100:+.2f} نقطة مئوية، "
                  f"وفقدان {n_all - kn} قرار ({(n_all-kn)/n_all*100:.0f}% من حجم الإشارات)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
