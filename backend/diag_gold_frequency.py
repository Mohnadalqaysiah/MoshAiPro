"""
(2026-10-14) تشخيص للقراءة فقط: كم إشارة ذهب/فضة تصدر يومياً، وهل قلّت بعد فلاتر 10/10؟

بلاغ المالك: إشارة ذهب واحدة فقط منذ افتتاح الاثنين 12/10 وخسرت. فلتران للمعادن دخلا 10/10:
COMMODITY_COUNTER_4H_TREND و SL_INSIDE_SPREAD_NOISE. سجلات الحاوية تُمسح بكل إعادة نشر، أما
جدول signals فدائم — نعدّ القرارات الفريدة يومياً (حسب الصدور) ونتائجها بمضاعف R.

    docker exec moshapi_backend python diag_gold_frequency.py [الرموز=XAUUSD,XAGUSD]
"""
import sys
from datetime import datetime, timezone

from app.database import SessionLocal
from app.models.signal import Signal
from app.services.decision_grouping import group_unique_decisions, merge_reissued
from app.services.quality_report import _r_multiple, OUTCOME_FIX_DATE

SYMS = [s.strip().upper() for s in (sys.argv[1] if len(sys.argv) > 1 else "XAUUSD,XAGUSD").split(",")]
FILTERS_FROM = datetime(2026, 10, 10, tzinfo=timezone.utc)
CLOSED = ("TP1_HIT", "TP2_HIT", "SL_HIT")


def _utc(d):
    return d if d is None or d.tzinfo else d.replace(tzinfo=timezone.utc)


def main():
    db = SessionLocal()
    for sym in SYMS:
        rows = db.query(Signal).filter(Signal.market == sym, Signal.created_at >= OUTCOME_FIX_DATE).all()
        by_id = {s.id: s for s in rows}
        decs = merge_reissued(group_unique_decisions(rows))
        days = {}
        for d in decs:
            day = _utc(d["created_at"]).date()
            s = by_id.get(d["id"])
            r = _r_multiple(s.entry_price, s.stop_loss, s.take_profit_1, s.take_profit_2, d["status"]) \
                if s and d["status"] in CLOSED else None
            days.setdefault(day, []).append((d["signal_type"], d["timeframe"], d["status"], r))

        print(f"══ {sym} — قرارات فريدة يومياً (حسب الصدور، UTC) ══")
        before, after = [], []
        for day in sorted(days):
            xs = days[day]
            (after if day >= FILTERS_FROM.date() else before).append(len(xs))
            rs = [x[3] for x in xs if x[3] is not None]
            sides = f"شراء {sum(1 for x in xs if x[0] == 'BUY')} / بيع {sum(1 for x in xs if x[0] == 'SELL')}"
            mark = "  ← بعد فلاتر 10/10" if day == FILTERS_FROM.date() else ""
            print(f"  {day} {day.strftime('%a')}  {len(xs):>2} قرار | {sides} | "
                  f"مغلقة {len(rs)} مجموع {sum(rs):+.1f}R{mark}")
        trading = lambda xs: [x for x in xs if x > 0]
        b, a = trading(before), trading(after)
        print(f"  ◂ متوسط قبل 10/10: {sum(b) / len(b) if b else 0:.1f} قرار/يوم نشط | "
              f"بعدها: {sum(a) / len(a) if a else 0:.1f} قرار/يوم نشط ({len(a)} يوم)\n")
    db.close()


if __name__ == "__main__":
    main()
