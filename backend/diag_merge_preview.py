"""
(2026-10-15) مع وسيط "wide": يقارن الدمج الحالي بالدمج الموسّع (نفس الوقف والهدف، دخول ≤0.5%):
    docker exec moshapi_backend python diag_merge_preview.py wide

(2026-10-12) معاينة للقراءة فقط: أثر دمج "الصفقة المُعاد إصدارها" على الإحصائيات.

القاعدة (decision_grouping.merge_reissued): نفس الرمز والاتجاه، دخول ضمن 0.05%، أي فريم،
والثانية صدرت والأولى ما زالت مفتوحة → قرار واحد بنتيجة الأولى. متماثلة على الرابح والخاسر.

يطبع قبل/بعد منذ OUTCOME_FIX_DATE: المجموع، ما دُمج (رابح/خاسر — فحص التماثل)، حسب الأسبوع،
وإعادة حساب قاعدة كريبتو العطلة بعد الدمج. لا يكتب شيئاً.

    docker exec moshapi_backend python diag_merge_preview.py
"""
import sys
from datetime import timezone

from app.database import SessionLocal
from app.models.market_config import MarketConfig
from app.models.signal import Signal, SignalStatus
from app.services.decision_grouping import group_unique_decisions, merge_reissued
from app.services.quality_report import _r_multiple, OUTCOME_FIX_DATE


def _utc(d):
    return d if d is None or d.tzinfo else d.replace(tzinfo=timezone.utc)


def main():
    db = SessionLocal()
    rows = db.query(Signal).filter(
        Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT]),
        Signal.created_at >= OUTCOME_FIX_DATE,
    ).all()
    verified = [s for s in rows if s.current_price is not None or getattr(s, "outcome_verified", False)]
    by_id = {s.id: s for s in verified}

    def R(d):
        s = by_id.get(d["id"])
        return _r_multiple(s.entry_price, s.stop_loss, s.take_profit_1, s.take_profit_2, d["status"]) if s else None

    WIDE = len(sys.argv) > 1 and sys.argv[1] == "wide"
    if WIDE:
        print("وضع المقارنة: قبل = الدمج الحالي (0.05%) ، بعد = الدمج الموسّع (نفس الوقف والهدف، دخول ≤0.5%)\n")
        before = merge_reissued(group_unique_decisions(verified), wide=False)
        after = merge_reissued([dict(d, merged_count=0, merged_row_ids=[], merge_conflict=False) for d in group_unique_decisions(verified)], wide=True)
    else:
        before = group_unique_decisions(verified)
        after = merge_reissued(before)
    kept_ids = {d["id"] for d in after}
    removed = [d for d in before if d["id"] not in kept_ids]

    def summary(name, ds):
        rs = [r for r in (R(d) for d in ds) if r is not None]
        w = sum(1 for r in rs if r > 0)
        n = len(rs)
        print(f"{name:<8} {n:>4} قرار | رابحة {w:>3} | خاسرة {n - w:>3} | نجاح {w / n * 100 if n else 0:4.1f}% | "
              f"مجموع {sum(rs):+8.2f}R | متوسط {sum(rs) / n if n else 0:+.3f}R")
        return n, sum(rs)

    print(f"منذ {OUTCOME_FIX_DATE:%Y-%m-%d} — قرارات مغلقة موثّقة\n")
    summary("قبل", before)
    summary("بعد", after)

    rr = [R(d) for d in removed]
    rw = sum(1 for r in rr if r is not None and r > 0)
    rl = sum(1 for r in rr if r is not None and r <= 0)
    conflicts = sum(1 for d in after if d.get("merge_conflict"))
    same_tf = 0
    for h in after:
        if not h.get("merged_count"):
            continue
        for d in removed:
            if d["market"] == h["market"] and d["signal_type"] == h["signal_type"] and d["timeframe"] == h["timeframe"] \
                    and set(d["row_ids"]) <= set(h["merged_row_ids"]):
                same_tf += 1
    print(f"\nدُمج {len(removed)} قراراً مكرراً: رابحة {rw} | خاسرة {rl}  ← فحص التماثل")
    print(f"  على نفس الفريم: {same_tf} | على فريم آخر: {len(removed) - same_tf}")
    print(f"  نتيجة المكرر خالفت الأولى: {conflicts} (تُحسب نتيجة الأولى)")

    print("\nحسب أسبوع الصدور (قبل → بعد):")
    def weekly(ds):
        out = {}
        for d in ds:
            r = R(d)
            if r is None:
                continue
            k = _utc(d["created_at"]).isocalendar()[:2]
            n, t = out.get(k, (0, 0.0))
            out[k] = (n + 1, t + r)
        return out
    wb, wa = weekly(before), weekly(after)
    for k in sorted(wb):
        nb, tb = wb[k]
        na, ta = wa.get(k, (0, 0.0))
        print(f"  W{k[1]}/{k[0]}: {nb:>3} قرار {tb:+7.2f}R  →  {na:>3} قرار {ta:+7.2f}R")

    crypto = {r[0].upper() for r in db.query(MarketConfig.symbol).filter(MarketConfig.category == "crypto").all()}
    def cw(ds):
        rs = [R(d) for d in ds if (d["market"] or "").upper() in crypto and _utc(d["created_at"]).weekday() >= 5]
        rs = [r for r in rs if r is not None]
        return len(rs), (sum(rs) / len(rs) if rs else 0.0)
    nb, ab = cw(before)
    na, aa = cw(after)
    print(f"\nقاعدة كريبتو العطلة (≥30 قراراً ومتوسط أسوأ من −0.2R):")
    print(f"  قبل الدمج: {nb} قرار، متوسط {ab:+.2f}R | بعد الدمج: {na} قرار، متوسط {aa:+.2f}R"
          f"  ← {'ما زالت متحققة' if na >= 30 and aa < -0.2 else 'لم تعد متحققة'}")

    if WIDE:
        print("\nكل ما يدمجه التوسيع (المكرر ← الأولى التي تُحسب):")
        for d in sorted(removed, key=lambda x: _utc(x["created_at"])):
            h = next((x for x in after if set(d.get("row_ids") or [d["id"]]) & set(x.get("merged_row_ids") or [])), None)
            if not h:
                continue
            rd, rh = R(d), R(h)
            fr = lambda r: "—" if r is None else f"{r:+.2f}R"
            print(f"  {d['market']:<8} {d['signal_type']:<4} | الأولى {_utc(h['created_at']):%m-%d %H:%M} {h['timeframe']:<4} "
                  f"دخول {h['entry_price']} وقف {h['stop_loss']} {h['status']} {fr(rh)} "
                  f"| المكرر {_utc(d['created_at']):%m-%d %H:%M} {d['timeframe']:<4} دخول {d['entry_price']} وقف {d['stop_loss']} "
                  f"{d['status']} {fr(rd)}{'  ⚠️ نتيجة مختلفة' if d['status'] != h['status'] else ''}")
        db.close()
        return

    print("\nأمثلة على ما دُمج (أول 15):")
    shown = 0
    for h in sorted([d for d in after if d.get("merged_count")], key=lambda d: _utc(d["created_at"]), reverse=True):
        print(f"  {h['market']:<8} {h['signal_type']:<4} {h['timeframe']:<4} {_utc(h['created_at']):%m-%d %H:%M} "
              f"{h['status']:<8} + {h['merged_count']} مكرر{' ⚠️ نتيجة مختلفة' if h.get('merge_conflict') else ''}")
        shown += 1
        if shown >= 15:
            break
    db.close()


if __name__ == "__main__":
    main()
