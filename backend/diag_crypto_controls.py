"""
(2026-10-13) محاكاة للقراءة فقط: ضوابط مخاطرة للكريبتو لا تعتمد على تخمين اتجاه السوق.

السياق: آخر يومين 23 قرار كريبتو، 1 رابح، −18.9R — شراء متكرر في سوق هابط. فلتر الاتجاه
مرفوض للكريبتو (DECISIONS 10/10: عكس الاتجاه كان الأربح للكريبتو، ADA +23.6R ...) وقد
يعود السوق ارتدادياً. نقيس بدلاً منه ضوابط تعمل بأي حالة سوق:

  A) قاطع الخسائر: بعد N خسائر متتالية بنفس (رمز، اتجاه) لا إشارة بنفسهما لمدة H ساعة
     من إغلاق آخر خسارة (الحالي بالإنتاج: 3 خسائر، 6 ساعات — مُطبَّق أصلاً بالأساس).
  B) سقف التزامن: لا أكثر من K قرار كريبتو مفتوح بنفس الاتجاه بنفس الوقت (الكريبتو يتحرك معاً).

المحاكاة على النتائج المسجّلة: القرار الممنوع يُحذف، الباقي بنتيجته. تقريب — في الواقع
منع صفقة قد يغيّر توقيت ما بعدها — لكنه كافٍ لمقارنة السيناريوهات على نفس البيانات.
المهم: أثر كل ضابط على **الفترة الجيدة** (قبل آخر يومين) لا على آخر يومين فقط.

    docker exec moshapi_backend python diag_crypto_controls.py
"""
from datetime import datetime, timedelta, timezone

from app.database import SessionLocal
from app.models.market_config import MarketConfig
from app.models.signal import Signal, SignalStatus
from app.services.decision_grouping import verified_unique_decisions
from app.services.quality_report import _r_multiple, OUTCOME_FIX_DATE

RECENT_DAYS = 2


def _utc(d):
    return d if d is None or d.tzinfo else d.replace(tzinfo=timezone.utc)


def load(db):
    crypto = {r[0].upper() for r in db.query(MarketConfig.symbol).filter(MarketConfig.category == "crypto").all()}
    rows = db.query(Signal).filter(
        Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT]),
        Signal.created_at >= OUTCOME_FIX_DATE,
    ).all()
    by_id = {s.id: s for s in rows}
    out = []
    for d in verified_unique_decisions(rows):
        if (d["market"] or "").upper() not in crypto:
            continue
        s = by_id.get(d["id"])
        r = _r_multiple(s.entry_price, s.stop_loss, s.take_profit_1, s.take_profit_2, d["status"]) if s else None
        if r is None or not d["exit_executed"]:
            continue
        out.append(dict(m=d["market"], side=d["signal_type"], t=_utc(d["created_at"]),
                        x=_utc(d["exit_executed"]), r=r, sl=d["status"] == "SL_HIT"))
    return sorted(out, key=lambda e: e["t"])


def simulate(events, streak_n=None, streak_h=None, cap=None):
    kept = []
    for e in events:
        if streak_n:
            prev = [k for k in kept if k["m"] == e["m"] and k["side"] == e["side"] and k["x"] <= e["t"]]
            prev.sort(key=lambda k: k["x"])
            last = prev[-streak_n:]
            if len(last) == streak_n and all(k["sl"] for k in last) \
                    and e["t"] - last[-1]["x"] < timedelta(hours=streak_h):
                continue
        if cap:
            open_same = sum(1 for k in kept if k["side"] == e["side"] and k["t"] <= e["t"] < k["x"])
            if open_same >= cap:
                continue
        kept.append(e)
    return kept


def main():
    db = SessionLocal()
    ev = load(db)
    cut = datetime.now(timezone.utc) - timedelta(days=RECENT_DAYS)

    scenarios = [
        ("الأساس (كما حدث)", {}),
        ("قاطع 3 خسائر / 24 ساعة", dict(streak_n=3, streak_h=24)),
        ("قاطع 2 خسارة / 24 ساعة", dict(streak_n=2, streak_h=24)),
        ("قاطع 2 خسارة / 12 ساعة", dict(streak_n=2, streak_h=12)),
        ("سقف 2 مفتوحة بنفس الاتجاه", dict(cap=2)),
        ("سقف 3 مفتوحة بنفس الاتجاه", dict(cap=3)),
        ("سقف 4 مفتوحة بنفس الاتجاه", dict(cap=4)),
        ("قاطع 3/24 + سقف 3", dict(streak_n=3, streak_h=24, cap=3)),
        ("قاطع 2/24 + سقف 3", dict(streak_n=2, streak_h=24, cap=3)),
    ]
    print(f"قرارات الكريبتو المغلقة منذ {OUTCOME_FIX_DATE:%Y-%m-%d}: {len(ev)}  (آخر {RECENT_DAYS} يوم = حسب الإغلاق)\n")
    print(f"{'السيناريو':<28}{'كل الفترة':>26}   {'قبل آخر يومين':>24}   {'آخر يومين':>20}")
    for name, kw in scenarios:
        k = simulate(ev, **kw)
        old = [e for e in k if e["x"] < cut]
        new = [e for e in k if e["x"] >= cut]
        f = lambda xs: f"{len(xs):>4} | {sum(e['r'] for e in xs):+7.2f}R ({(sum(e['r'] for e in xs) / len(xs)) if xs else 0:+.2f})"
        print(f"{name:<28}{f(k):>26}   {f(old):>24}   {f(new):>20}")

    print("\nحسب الأسبوع (R): الأساس ← قاطع 3/24 + سقف 3")
    base = simulate(ev)
    best = simulate(ev, streak_n=3, streak_h=24, cap=3)
    def wk(xs):
        o = {}
        for e in xs:
            key = e["t"].isocalendar()[:2]
            o[key] = o.get(key, 0.0) + e["r"]
        return o
    wb, wa = wk(base), wk(best)
    for key in sorted(wb):
        print(f"  W{key[1]}/{key[0]}: {wb[key]:+7.2f}R  ←  {wa.get(key, 0.0):+7.2f}R")
    db.close()


if __name__ == "__main__":
    main()
