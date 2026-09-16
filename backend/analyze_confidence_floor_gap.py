"""
analyze_confidence_floor_gap.py
==================================
تحليل قراءة فقط — يقيس حجم ثغرة أرضية الثقة قبل أي تعديل عليها.

الثغرة (مؤكدة بالكود ومشاهَدة حيّة 15/09): ترتيب التنفيذ بـanalyze_market
  1) _institutional_gate → Rule 5 يرفض أي ثقة < 55%
  2) _output_safety_gate
  3) _confidence_calibration_layer → يستبدل الثقة بالكامل
     (analysis["ai_confidence_score"] = final_conf، السطر 2975)
الأرضية تُفحص على القيمة الخام قبل إعادة الحساب، ولا يعيد أحد فحصها
بعدها. شوهدت حيّاً: XAGUSD/15m أصدرت SELL بثقة نهائية 23.5%.

⚠️ لماذا لا أُصلحها مباشرة: تحليل سابق بنفس الجلسة أظهر أن شريحة الثقة
تحت 60% لم تكن الأسوأ — بل كانت expectancy أعلى من شريحة 65-75%. أي
أن فرض الأرضية قد **يحذف إشارات رابحة**. خمس فرضيات سقطت بهذه الجلسة
لأنها بُنيت على حدس بدل قياس، فلن أكرّرها.

يقيس: كم إشارة منشورة كانت ثقتها النهائية تحت الأرضية، وكيف كان أداؤها
مقارنة بما فوقها — بالعيّنة وبالتوزيع على الرموز.

التشغيل:
  docker cp analyze_confidence_floor_gap.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/analyze_confidence_floor_gap.py
"""
import sys
sys.path.insert(0, "/app")

from datetime import datetime, timezone
from collections import Counter
from app.database import SessionLocal
from app.models.signal import Signal
from app.services.decision_grouping import verified_unique_decisions

CUTOFF     = datetime(2026, 8, 18, tzinfo=timezone.utc)
CLOSED     = {"TP1_HIT", "TP2_HIT", "SL_HIT"}
FLOOR      = 55.0
MIN_SAMPLE = 15

BANDS = [(0, 40, "أقل من 40%"), (40, 55, "40-55% (تحت الأرضية)"),
         (55, 65, "55-65%"), (65, 75, "65-75%"), (75, 101, "75%+")]


def show(label, rows):
    n = len(rows)
    if not n:
        print(f"  {label:<24} n=  0")
        return
    wins = sum(1 for d in rows if d["status"] in ("TP1_HIT", "TP2_HIT"))
    pts  = sum(d["points"] for d in rows)
    mix  = ", ".join(f"{s}×{c}" for s, c in Counter(d["market"] for d in rows).most_common(4))
    warn = f"  ⚠️ عينة {n} < {MIN_SAMPLE}" if n < MIN_SAMPLE else ""
    print(f"  {label:<24} n={n:>3d}  winrate={wins/n*100:>5.1f}%  نقاط={pts:>+9.2f}  "
          f"exp={pts/n:>+7.2f}{warn}")
    print(f"  {'':<24} {mix}")


def main():
    db = SessionLocal()
    try:
        signals   = db.query(Signal).filter(Signal.created_at >= CUTOFF).all()
        decisions = [d for d in verified_unique_decisions(signals) if d["status"] in CLOSED]

        print("=" * 92)
        print(f"ثقة الإشارات المنشورة فعلاً — منذ {CUTOFF.date()}")
        print("=" * 92)
        n = len(decisions)
        wins = sum(1 for d in decisions if d["status"] in ("TP1_HIT", "TP2_HIT"))
        pts  = sum(d["points"] for d in decisions)
        print(f"  الأساس: n={n}  winrate={wins/n*100:.1f}%  نقاط={pts:+.2f}\n")

        for lo, hi, label in BANDS:
            show(label, [d for d in decisions
                         if lo <= float(d.get("ai_confidence") or 0) < hi])

        below = [d for d in decisions if float(d.get("ai_confidence") or 0) < FLOOR]
        above = [d for d in decisions if float(d.get("ai_confidence") or 0) >= FLOOR]

        print("\n" + "=" * 92)
        print(f"المقارنة الحاسمة — تحت الأرضية ({FLOOR:.0f}%) مقابل فوقها")
        print("=" * 92)
        show("تحت الأرضية", below)
        show("عند الأرضية أو فوقها", above)

        if below and above:
            bn = len(below)
            bw = sum(1 for d in below if d["status"] in ("TP1_HIT", "TP2_HIT"))
            bp = sum(d["points"] for d in below)
            print("\n" + "-" * 92)
            print(f"  نسبة الإشارات المنشورة تحت الأرضية المعلنة: {bn}/{n} = {bn/n*100:.1f}%")
            print(f"  لو فُرضت الأرضية بعد إعادة الحساب، كنا سنفقد {bn} قراراً "
                  f"({bw} رابح) و{bp:+.2f} نقطة.")
            rest_p = pts - bp
            rest_n = n - bn
            print(f"  الأرقام الناتجة عندها: n={rest_n}  "
                  f"winrate={(wins-bw)/rest_n*100:.1f}%  نقاط={rest_p:+.2f}")
            verdict = ("فرض الأرضية يحسّن النتيجة"
                       if bp < 0 else "فرض الأرضية يحذف ربحاً — لا يُنصح به")
            print(f"  ⇒ {verdict}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
