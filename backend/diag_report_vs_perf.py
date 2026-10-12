"""
(2026-10-12) تشخيص للقراءة فقط: لماذا يختلف "تقرير آخر يوم" بالداشبورد عن صفحة الأداء؟

تقرير الداشبورد (admin.get_performance_report): صفقات أُغلقت (exit_executed) آخر 24 ساعة،
  كل الرموز، group_unique_decisions (يشمل التحديد اليدوي غير المؤكد).
صفحة الأداء (signals.get_signal_performance): صفقات صدرت (created_at) هذا الأسبوع/اليوم
  بتوقيت UTC، verified_unique_decisions (يستبعد غير المؤكد)، مفلترة بقائمة المستخدم.

يطبع كل قرار من التقرير وهل يدخل صفحة الأداء، وإن لم يدخل فلماذا، ومجموع R للطرفين.
لا يكتب شيئاً بقاعدة البيانات.

    docker exec moshapi_backend python diag_report_vs_perf.py [--days 1]
"""
import argparse
from datetime import datetime, timedelta, timezone

from app.database import SessionLocal
from app.models.signal import Signal, SignalStatus
from app.services.decision_grouping import group_unique_decisions
from app.services.quality_report import _r_multiple, OUTCOME_FIX_DATE


def _utc(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=1)
    args = ap.parse_args()

    db = SessionLocal()
    now = datetime.now(timezone.utc)
    today = now.date()
    week_start = datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time()).replace(tzinfo=timezone.utc)
    day_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
    closed = [SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT]

    rows = (db.query(Signal)
              .filter(Signal.status.in_(closed), Signal.exit_executed >= now - timedelta(days=args.days))
              .all())
    by_id = {s.id: s for s in rows}
    decisions = group_unique_decisions(rows)
    decisions.sort(key=lambda d: _utc(d["exit_executed"]) or now)

    print(f"الآن UTC: {now:%Y-%m-%d %H:%M} | بداية الأسبوع: {week_start:%Y-%m-%d} | بداية اليوم: {day_start:%Y-%m-%d}")
    print(f"قرارات التقرير: {len(decisions)}\n")
    print(f"{'الرمز':<9}{'فريم':<5}{'نوع':<5}{'نتيجة':<8}{'R':>6}  {'صدرت UTC':<12}{'أُغلقت UTC':<12}بصفحة الأداء؟")

    rep_r = perf_r = 0.0
    perf_n = perf_w = 0
    reasons_count = {}
    for d in decisions:
        group_rows = [by_id[i] for i in d["row_ids"]]
        rep = by_id[d["id"]]
        r = _r_multiple(rep.entry_price, rep.stop_loss, rep.take_profit_1, rep.take_profit_2, d["status"])
        rep_r += r or 0
        created = _utc(d["created_at"])
        verified = any(s.current_price is not None or getattr(s, "outcome_verified", False) for s in group_rows)

        reasons = []
        if created < week_start:
            reasons.append("صدرت قبل بداية الأسبوع")
        elif created < day_start:
            reasons.append("صدرت قبل اليوم (تدخل الأسبوع لا اليوم)")
        if created < OUTCOME_FIX_DATE:
            reasons.append("قبل تاريخ البيانات الموثوقة")
        if not verified:
            reasons.append("نتيجة يدوية غير مؤكدة")
        in_week = created >= week_start and verified
        if in_week:
            perf_n += 1
            perf_w += d["status"] != "SL_HIT"
            perf_r += r or 0
        for x in reasons:
            reasons_count[x] = reasons_count.get(x, 0) + 1

        mark = "✅ نعم" if in_week and not reasons else ("✅ بالأسبوع — " + "، ".join(reasons) if in_week else "❌ لا — " + "، ".join(reasons))
        print(f"{str(d['market']):<9}{str(d['timeframe']):<5}{str(d['signal_type']):<5}{str(d['status']):<8}"
              f"{(r if r is not None else 0):>+6.2f}  {created:%d/%m %H:%M}  {_utc(d['exit_executed']):%d/%m %H:%M}  {mark}")

    print("\n── الخلاصة ──")
    print(f"التقرير: {len(decisions)} قرار، مجموع {rep_r:+.2f}R")
    print(f"منها ما يدخل أسبوع صفحة الأداء: {perf_n} قرار ({perf_w} رابحة)، مجموع {perf_r:+.2f}R")
    for k, v in reasons_count.items():
        print(f"  {k}: {v}")
    db.close()


if __name__ == "__main__":
    main()
