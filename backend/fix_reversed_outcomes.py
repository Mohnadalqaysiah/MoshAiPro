"""
fix_reversed_outcomes.py
===========================
يصحّح الصفوف (كل مستخدم مرتبط) لثلاث قرارات مؤكد انعكاسها بالتحقيق
الكامل (analyze_delayed_outcome_risk.py + verify_sl_tp_order_fix.py):
  - #2168 XAUUSD 4h  — كان SL_HIT، الصحيح TP1_HIT
  - #2269 SNB    15m — كان TP2_HIT، الصحيح SL_HIT
  - #2164 XAGUSD 1h  — كان TP2_HIT، الصحيح SL_HIT

لكل صف: يصحّح status، يعيد حساب points_earned/profit_loss/
profit_loss_percentage بالمستوى الحقيقي (نفس _calc_points الحيّة من
admin.py)، يعلّم outcome_verified=True (نفس علامة "تصحيح مؤكد بالسعر
الحقيقي" المستخدمة بأداة "🔍 تحقق" — تُحتسب بكل تقارير الأداء)،
ويوثّق التصحيح بحقل notes مع القيمة الأصلية.

⚠️ افتراضياً DRY-RUN. لازم --apply صراحة للتنفيذ الفعلي.

التشغيل:
  docker cp fix_reversed_outcomes.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/fix_reversed_outcomes.py            # dry-run
  docker exec moshapi_backend python /app/fix_reversed_outcomes.py --apply    # تطبيق فعلي
"""
import sys
sys.path.insert(0, "/app")

from datetime import datetime, timedelta, timezone
from app.database import SessionLocal
from app.models.signal import Signal, SignalStatus
from app.services.decision_grouping import decision_key
from app.api.admin import _calc_points

# قرار#id ممثّل -> الحالة الصحيحة المؤكدة بالتحقيق
CORRECTIONS = {
    2168: "TP1_HIT",   # XAUUSD 4h
    2269: "SL_HIT",    # SNB 15m
    2164: "SL_HIT",    # XAGUSD 1h
}


def main():
    apply = "--apply" in sys.argv
    db = SessionLocal()
    try:
        reps = db.query(Signal).filter(Signal.id.in_(list(CORRECTIONS.keys()))).all()
        total_rows = 0

        for rep in reps:
            correct_status_str = CORRECTIONS[rep.id]
            correct_status = SignalStatus(correct_status_str)

            entry = float(rep.entry_price)
            sl    = float(rep.stop_loss)
            tp1   = float(rep.take_profit_1)
            tp2   = float(rep.take_profit_2 or tp1)
            is_buy = (rep.signal_type.value if hasattr(rep.signal_type, "value") else rep.signal_type) == "BUY"

            if correct_status == SignalStatus.SL_HIT:
                diff, exit_price = abs(entry - sl), sl
            elif correct_status == SignalStatus.TP2_HIT:
                diff, exit_price = abs(tp2 - entry), tp2
            else:
                diff, exit_price = abs(tp1 - entry), tp1

            points = _calc_points(rep.market, diff, entry)
            if correct_status == SignalStatus.SL_HIT:
                points = -points
            pnl_pct = round((exit_price - entry) / entry * 100, 3) if is_buy \
                      else round((entry - exit_price) / entry * 100, 3)

            created = rep.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            rep_key = decision_key(rep.market, rep.timeframe, rep.signal_type, rep.entry_price)

            # نطاق بحث أوسع (±2 دقيقة، نفس نافذة التجميع بالتطبيق)، وبعدين
            # نفلتر بمفتاح القرار الدقيق بايثون لتجنّب مقارنة float بـSQL مباشرة
            candidates = (
                db.query(Signal)
                .filter(
                    Signal.market == rep.market,
                    Signal.timeframe == rep.timeframe,
                    Signal.signal_type == rep.signal_type,
                    Signal.created_at >= created - timedelta(minutes=2),
                    Signal.created_at <= created + timedelta(minutes=2),
                )
                .all()
            )
            siblings = [s for s in candidates if decision_key(s.market, s.timeframe, s.signal_type, s.entry_price) == rep_key]

            print(f"\nقرار#{rep.id} {rep.market} ({rep.timeframe}) — {len(siblings)} صف مرتبط:")
            for s in siblings:
                old_status = s.status.value if hasattr(s.status, "value") else s.status
                old_points = s.points_earned
                note = (
                    f" [صُحح 2026-09-12 — كان معكوساً بسبب خلل ترتيب فحص SL/TP "
                    f"(فحص أقصى/أدنى سعر لكامل نافذة التحقق بدل الترتيب الزمني الصحيح، "
                    f"بفجوة تحقق طويلة بسبب توقف حلقة الفحص). القيمة الأصلية: "
                    f"status={old_status}, points={old_points}]"
                )
                print(f"  صف#{s.id}: {old_status} ({old_points}) → {correct_status_str} ({points:+.2f})"
                      + ("" if apply else "  [DRY-RUN]"))
                if apply:
                    s.status = correct_status
                    s.points_earned = round(points, 2)
                    s.profit_loss = round(points, 2)
                    s.profit_loss_percentage = pnl_pct
                    s.outcome_verified = True
                    s.notes = (s.notes or "") + note
                    total_rows += 1

        if apply:
            db.commit()
            print(f"\n✅ تم تصحيح {total_rows} صف بقاعدة البيانات.")
        else:
            print(f"\nℹ️  dry-run — لم يُعدَّل شيء. شغّل بـ--apply للتنفيذ الفعلي.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
