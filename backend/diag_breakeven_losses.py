"""
(2026-10-16) معاينة للقراءة فقط: صفقات وصلتها رسالة التأمين ("انقل الوقف للدخول" عند +1R) ثم سُجّلت خاسرة (SL_HIT).

سؤال المالك: لو حُسبت هذه "تعادل" (0R) بدل خسارة (−1R) — لأن المنصة طلبت من العميل نقل الوقف للدخول فعلاً — كم تتغيّر
الأرقام؟ منذ 14/10 TP1 = 1R = نقطة رسالة التأمين، فالمسألة تخص صفقات ما قبل 14/10 عملياً.
القرارات الفريدة نفسها التي تستخدمها التقارير (verified_unique_decisions). القرار "وصلته رسالة تأمين" إن كان أي صف منه
be_alert_sent=True. لا يكتب شيئاً.

    docker exec moshapi_backend python diag_breakeven_losses.py
"""
from datetime import timezone

from app.database import SessionLocal
from app.models.market_config import MarketConfig
from app.models.signal import Signal, SignalStatus
from app.services.decision_grouping import verified_unique_decisions
from app.services.quality_report import _r_multiple, OUTCOME_FIX_DATE

NAMES = {"crypto": "كريبتو", "forex": "فوركس", "commodity": "سلع ومؤشرات", "index": "مؤشرات",
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
    decs = verified_unique_decisions(rows)

    total_r, n_all, wins_all = 0.0, 0, 0
    affected = []
    weekly = {}
    for d in decs:
        s = by_id.get(d["id"])
        r = _r_multiple(s.entry_price, s.stop_loss, s.take_profit_1, s.take_profit_2, d["status"]) if s else None
        if r is None:
            continue
        ids = (d.get("row_ids") or [d["id"]]) + (d.get("merged_row_ids") or [])
        be = any(getattr(by_id.get(i), "be_alert_sent", False) for i in ids if i in by_id)
        hit = d["status"] == "SL_HIT" and be
        n_all += 1
        wins_all += r > 0
        total_r += r
        w = _utc(d["created_at"]).isocalendar()[:2]
        nb, rb, na, ra = weekly.get(w, (0, 0.0, 0, 0.0))
        weekly[w] = (nb + 1, rb + r, na + 1, ra + (0.0 if hit else r))
        if hit:
            affected.append((d, cat.get((d["market"] or "").upper(), "?")))

    k = len(affected)
    print(f"منذ {OUTCOME_FIX_DATE:%Y-%m-%d} — {n_all} قراراً مغلقاً موثّقاً\n")
    print(f"وصلتها رسالة تأمين ثم سُجّلت خاسرة: {k} قراراً")
    if not n_all:
        return
    print(f"  الآن:            ربح {wins_all}/{n_all} = {wins_all / n_all * 100:.1f}% | مجموع {total_r:+.1f}R | متوسط {total_r / n_all:+.3f}R")
    print(f"  لو حُسبت تعادلاً: ربح {wins_all}/{n_all - k} قرار حُسم = {wins_all / max(1, n_all - k) * 100:.1f}% "
          f"(التعادل خارج النسبة) | مجموع {total_r + k:+.1f}R | متوسط {(total_r + k) / n_all:+.3f}R")
    print("\n  حسب السوق:")
    by_cat = {}
    for _, c in affected:
        by_cat[c] = by_cat.get(c, 0) + 1
    for c, n in sorted(by_cat.items(), key=lambda x: -x[1]):
        print(f"    {NAMES.get(c, c):<12} {n} قرار (+{n}R)")
    print("\n  حسب أسبوع الصدور (الآن → لو تعادل):")
    for w in sorted(weekly):
        nb, rb, na, ra = weekly[w]
        print(f"    W{w[1]}/{w[0]}: {rb:+7.1f}R → {ra:+7.1f}R")
    print("\n  الصفقات:")
    for d, c in sorted(affected, key=lambda x: _utc(x[0]["created_at"])):
        print(f"    #{d['id']:<5} {d['market']:<10} {d['timeframe']:<4} {d['signal_type']:<4} {_utc(d['created_at']):%m-%d %H:%M} "
              f"{NAMES.get(c, c)}")
    after_cap = sum(1 for d, _ in affected if _utc(d["created_at"]).date().isoformat() >= "2026-10-14")
    print(f"\n  منها بعد 14/10 (تقريب الهدف): {after_cap} — المتوقع ~0 (رسالة التأمين = الهدف الأول)")
    db.close()


if __name__ == "__main__":
    main()
