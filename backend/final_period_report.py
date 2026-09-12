"""
final_period_report.py
=========================
تقرير قراءة فقط — الرقم النهائي الدقيق لأداء الفترة منذ 2026-08-18،
بعد كل تصحيحات اليوم (12 صف انعكاس ترتيب SL/TP + 42 صف EXPIRED
مُتحقَّق منها). يستخدم نفس verified_unique_decisions() المستخدمة بكل
تقرير أداء حقيقي بالمنصة (الموقع العام، البوت، لوحة الأدمن) — نفس
الرقم بالضبط يلي رح يشوفه أي عميل أو تقرير.

التشغيل:
  docker cp final_period_report.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/final_period_report.py
"""
import sys
sys.path.insert(0, "/app")

from datetime import datetime, timezone
from app.database import SessionLocal
from app.models.signal import Signal
from app.services.decision_grouping import verified_unique_decisions

CUTOFF = datetime(2026, 8, 18, tzinfo=timezone.utc)
CLOSED = {"TP1_HIT", "TP2_HIT", "SL_HIT"}


def main():
    db = SessionLocal()
    try:
        signals = db.query(Signal).filter(Signal.created_at >= CUTOFF).all()
        decisions = verified_unique_decisions(signals)
        closed = [d for d in decisions if d["status"] in CLOSED]

        wins   = [d for d in closed if d["status"] in ("TP1_HIT", "TP2_HIT")]
        losses = [d for d in closed if d["status"] == "SL_HIT"]
        total_pts = sum(d["points"] for d in closed)

        print(f"📊 التقرير النهائي — منذ {CUTOFF.date()} (بعد كل تصحيحات اليوم)")
        print(f"   إجمالي القرارات الفريدة: {len(decisions)}")
        print(f"   قرارات محسومة (TP/SL): {len(closed)}")
        print(f"   رابحة: {len(wins)}   خاسرة: {len(losses)}")
        print(f"   نسبة النجاح: {len(wins)/len(closed)*100:.1f}%" if closed else "   نسبة النجاح: —")
        print(f"   مجموع النقاط: {total_pts:+.2f}")
        print(f"   متوسط النقاط/قرار: {total_pts/len(closed):+.3f}" if closed else "")
    finally:
        db.close()


if __name__ == "__main__":
    main()
