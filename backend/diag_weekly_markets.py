"""
(2026-10-13) جدول للقراءة فقط: النتيجة أسبوعياً لكل سوق — مقياس صاحب المنتج.

الأسبوع حسب أسبوع الصدور (مثل صفحة الأداء)، القرارات الموثّقة الفريدة (مع دمج المكرر)، بمضاعف R.
لكل سوق: R كل أسبوع، وعدد الأسابيع الرابحة/الخاسرة. لا يكتب شيئاً.

    docker exec moshapi_backend python diag_weekly_markets.py
"""
from datetime import timezone

from app.database import SessionLocal
from app.models.market_config import MarketConfig
from app.models.signal import Signal, SignalStatus
from app.services.decision_grouping import verified_unique_decisions
from app.services.quality_report import _r_multiple, OUTCOME_FIX_DATE

NAMES = {"crypto": "كريبتو", "forex": "فوركس", "commodity": "معادن وطاقة", "index": "مؤشرات",
         "stocks": "أسهم", "gulf": "خليجي"}


def _utc(d):
    return d if d is None or d.tzinfo else d.replace(tzinfo=timezone.utc)


def main():
    db = SessionLocal()
    cat = {r[0].upper(): (r[1] or "?") for r in db.query(MarketConfig.symbol, MarketConfig.category).all()}
    rows = db.query(Signal).filter(
        Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT]),
        Signal.created_at >= OUTCOME_FIX_DATE,
    ).all()
    by_id = {s.id: s for s in rows}
    cells, weeks, cats = {}, set(), set()
    for d in verified_unique_decisions(rows):
        s = by_id.get(d["id"])
        r = _r_multiple(s.entry_price, s.stop_loss, s.take_profit_1, s.take_profit_2, d["status"]) if s else None
        if r is None:
            continue
        w = _utc(d["created_at"]).isocalendar()[:2]
        c = cat.get((d["market"] or "").upper(), "?")
        weeks.add(w)
        cats.add(c)
        n, wins, tot = cells.get((w, c), (0, 0, 0.0))
        cells[(w, c)] = (n + 1, wins + (r > 0), tot + r)

    cats = sorted(cats, key=lambda c: -sum(cells.get((w, c), (0, 0, 0))[2] for w in weeks))
    head = "الأسبوع  " + "".join(f"{NAMES.get(c, c):>22}" for c in cats) + f"{'المجموع':>14}"
    print("R لكل أسبوع وسوق (عدد الصفقات بين قوسين)\n")
    print(head)
    for w in sorted(weeks):
        line = f"W{w[1]:<7}"
        total = 0.0
        for c in cats:
            n, _, t = cells.get((w, c), (0, 0, 0.0))
            total += t
            mark = "✅" if t > 0 else ("❌" if t < 0 else "  ")
            line += f"{(f'{t:+.1f}R ({n}) ' + mark) if n else '—':>22}"
        line += f"{total:>+12.1f}R"
        print(line)

    print("\nالأسابيع الرابحة/الخاسرة لكل سوق:")
    for c in cats:
        vals = [cells[(w, c)][2] for w in sorted(weeks) if (w, c) in cells]
        win = sum(1 for v in vals if v > 0)
        lose = sum(1 for v in vals if v < 0)
        print(f"  {NAMES.get(c, c):<14} رابحة {win} | خاسرة {lose} | أسوأ أسبوع {min(vals):+.1f}R | أفضل أسبوع {max(vals):+.1f}R")
    print("\nملاحظة: الأسبوع الحالي غير مكتمل، وصفقاته المفتوحة لم تُحسب بعد.")
    db.close()


if __name__ == "__main__":
    main()
