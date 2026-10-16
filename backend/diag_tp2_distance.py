"""
(2026-10-16) قياس للقراءة فقط: هل الهدف الثاني (TP2) بعيد بشكل غير واقعي؟ (بلاغ: AMD 15m بهدف +9.8%)

منذ 14/10 TP1 = 1R والهدف البعيد الأصلي صار TP2 — فلا يمسّ TP2 نسبة "الإشارة الرابحة" (تُحسم بـTP1)، لكنه يحدد كم
مرة تكتمل الصفقة لـTP2 وماذا يرى العميل. يقسم القرارات حسب بُعد TP2 بوحدات R وبنسبة السعر، ولكل شريحة: كم بلغ TP2،
كم توقف عند TP1، كم وقف، ومتوسط R. ثم يسرد أبعد الأهداف قياساً بالفريم. لا يكتب شيئاً — أي سقف لـTP2 يمسّ المحرك
المجمّد ويُقرَّر بقاعدة مسجّلة بعد هذا القياس.

    docker exec moshapi_backend python diag_tp2_distance.py
"""
from datetime import timezone

from app.database import SessionLocal
from app.models.signal import Signal, SignalStatus
from app.services.decision_grouping import verified_unique_decisions
from app.services.quality_report import _r_multiple, OUTCOME_FIX_DATE

R_BUCKETS = [(0, 2), (2, 3), (3, 5), (5, 8), (8, 1e9)]
# حركة "معقولة" خلال مدة الصفقة لكل فريم (نسبة من السعر) — مرجع للعرض فقط
TF_TYPICAL = {"15m": 1.0, "30m": 1.5, "1h": 2.0, "4h": 4.0, "1d": 8.0}


def _utc(d):
    return d if d is None or d.tzinfo else d.replace(tzinfo=timezone.utc)


def main():
    db = SessionLocal()
    rows = db.query(Signal).filter(
        Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT]),
        Signal.created_at >= OUTCOME_FIX_DATE,
    ).all()
    by_id = {s.id: s for s in rows}
    items = []
    for d in verified_unique_decisions(rows):
        s = by_id.get(d["id"])
        if not s or not s.take_profit_2:
            continue
        risk = abs(s.entry_price - s.stop_loss)
        if risk <= 0:
            continue
        tp2_r = abs(s.take_profit_2 - s.entry_price) / risk
        tp2_pct = abs(s.take_profit_2 - s.entry_price) / s.entry_price * 100
        r = _r_multiple(s.entry_price, s.stop_loss, s.take_profit_1, s.take_profit_2, d["status"])
        items.append((d, s, tp2_r, tp2_pct, r))

    for label, sel in (("كل الفترة منذ 16/09", lambda x: True),
                       ("بعد تقريب TP1 (منذ 14/10)", lambda x: _utc(x[0]["created_at"]).date().isoformat() >= "2026-10-14")):
        xs = [x for x in items if sel(x)]
        print("=" * 88 + f"\n{label}: {len(xs)} قراراً مغلقاً\n" + "=" * 88)
        print(f"{'بُعد TP2':<12}{'عدد':>6}{'بلغ TP2':>10}{'TP1 فقط':>10}{'وقف':>8}{'متوسط R':>10}{'مجموع R':>10}")
        for lo, hi in R_BUCKETS:
            b = [x for x in xs if lo <= x[2] < hi]
            if not b:
                continue
            t2 = sum(1 for x in b if x[0]["status"] == "TP2_HIT")
            t1 = sum(1 for x in b if x[0]["status"] == "TP1_HIT")
            sl = sum(1 for x in b if x[0]["status"] == "SL_HIT")
            rs = [x[4] for x in b if x[4] is not None]
            name = f"{lo:g}-{hi:g}R" if hi < 1e8 else f"≥{lo:g}R"
            print(f"{name:<12}{len(b):>6}{t2:>6} ({t2 / len(b) * 100:3.0f}%){t1:>10}{sl:>8}"
                  f"{(sum(rs) / len(rs) if rs else 0):>+10.2f}{sum(rs):>+10.1f}")
        print()

    print("أبعد الأهداف قياساً بحركة الفريم المعتادة (TP2 % ÷ المرجع):")
    ranked = sorted(items, key=lambda x: x[3] / TF_TYPICAL.get(x[1].timeframe, 2.0), reverse=True)[:15]
    for d, s, tp2_r, tp2_pct, r in ranked:
        print(f"  #{d['id']:<5} {s.market:<10} {s.timeframe:<4} {s.signal_type.value:<4} {_utc(s.created_at):%m-%d} | "
              f"TP2 على {tp2_pct:5.2f}% ({tp2_r:4.1f}R) — مرجع الفريم ~{TF_TYPICAL.get(s.timeframe, 2.0)}% | {d['status']}")
    db.close()


if __name__ == "__main__":
    main()
