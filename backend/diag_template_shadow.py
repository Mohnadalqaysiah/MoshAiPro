"""
(2026-10-15) تقرير للقراءة فقط: التجربة الصامتة لقوالب الذهب مقابل توصيات المحرك للذهب — أسبوعياً.

القوالب: صفقات سجّلتها app/services/template_shadow.py بعد 2026-10-16 (خارج عينة الاختبار)، بمحاسبة قابلة للتنفيذ
(نصف عند TP1 والوقف للدخول، خصم السبريد). المحرك: قرارات الذهب الموثّقة الفريدة بنفس الفترة، بـR حلقة الرصد —
وهي **متفائلة** (TP1 ثم وقف = ربح TP1 كامل)، فالمقارنة تميل لصالح المحرك.

شروط القبول (DECISIONS 15/10) لكل قالب: صافٍ موجب، 20 صفقة فأكثر، أغلب الأسابيع رابحة، أقصى تراجع < 6R.

    docker exec moshapi_backend python diag_template_shadow.py
"""
from datetime import timezone

from app.database import SessionLocal
from app.models.shadow_signal import ShadowSignal
from app.models.signal import Signal, SignalStatus
from app.services.decision_grouping import verified_unique_decisions
from app.services.quality_report import _r_multiple
from app.services.template_shadow import SHADOW_START

NAMES = {"gold_session_sell": "قنّاص — بيع", "gold_session_buy": "قنّاص — شراء",
         "gold_session_trend_buy": "قنّاص+اتجاه — شراء", "gold_session_trend_sell": "قنّاص+اتجاه — بيع"}
TP1 = ("TP2_HIT", "TP1_BE", "EXPIRED_TP1")


def _utc(d):
    return d if d is None or d.tzinfo else d.replace(tzinfo=timezone.utc)


def _week(d):
    y, w, _ = _utc(d).isocalendar()
    return f"{y}-W{w:02d}"


def _stats(items):
    """items = [(time, r, tp1_hit)] بالترتيب."""
    rs = [r for _, r, _ in items]
    eq = peak = dd = 0.0
    for r in rs:
        eq += r
        peak = max(peak, eq)
        dd = min(dd, eq - peak)
    weeks = {}
    for t, r, _ in items:
        weeks[_week(t)] = weeks.get(_week(t), 0.0) + r
    return {"n": len(rs), "net": sum(rs), "tp1": sum(1 for *_, h in items if h), "dd": dd, "weeks": weeks}


def _line(name, st):
    if not st["n"]:
        return f"{name:<22} لا صفقات بعد"
    won = sum(1 for v in st["weeks"].values() if v > 0)
    return (f"{name:<22} {st['n']:>4} صفقة | بلغت TP1 {100 * st['tp1'] / st['n']:>3.0f}% | صافي {st['net']:+6.2f}R | "
            f"متوسط {st['net'] / st['n']:+.3f}R | أسابيع رابحة {won}/{len(st['weeks'])} | أقصى تراجع {st['dd']:.2f}R")


def main():
    db = SessionLocal()
    print(f"التجربة الصامتة لقوالب الذهب منذ {SHADOW_START.date()} — لا شيء منها أُرسل لأي مشترك\n")
    rows = (db.query(ShadowSignal).filter(ShadowSignal.reason.like("tpl:%"))
              .order_by(ShadowSignal.created_at).all())
    table = {}
    for key, name in NAMES.items():
        items = [(s.created_at, s.r_multiple or 0.0, s.outcome in TP1) for s in rows if s.reason == f"tpl:{key}"]
        table[name] = _stats(items)

    eng = db.query(Signal).filter(
        Signal.market.in_(["XAUUSD", "XAU/USD"]), Signal.created_at >= SHADOW_START,
        Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT]),
    ).all()
    by_id = {s.id: s for s in eng}
    items = []
    for d in sorted(verified_unique_decisions(eng), key=lambda x: _utc(x["created_at"])):
        s = by_id.get(d["id"])
        r = _r_multiple(s.entry_price, s.stop_loss, s.take_profit_1, s.take_profit_2, d["status"]) if s else None
        if r is not None:
            items.append((d["created_at"], r, d["status"] in ("TP1_HIT", "TP2_HIT")))
    table["المحرك الحالي (متفائل)"] = _stats(items)

    for name, st in table.items():
        print(_line(name, st))

    weeks = sorted({w for st in table.values() for w in st["weeks"]})
    if weeks:
        print("\nR أسبوعياً:")
        print(f"{'':<22}" + "".join(f"{w:>12}" for w in weeks))
        for name, st in table.items():
            cells = [("%+.2fR" % st["weeks"][w]) if w in st["weeks"] else "—" for w in weeks]
            print(f"{name:<22}" + "".join(f"{c:>12}" for c in cells))

    print("\nتذكير: الحكم بعد أسبوعين على الأقل وبشروط القبول الأربعة. نتيجة أسبوع واحد ليست حكماً.")
    db.close()


if __name__ == "__main__":
    main()
