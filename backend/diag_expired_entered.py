"""
(2026-10-30) صفقات تفعّل دخولها ثم انتهت مدتها بلا هدف ولا وقف — هل تغيّر صورة سجل الأداء العام؟ للقراءة فقط.

سجل /results يقرأ closed_decisions (TP1/TP2/SL/BREAKEVEN)، فهذه الصفقات (status=EXPIRED مع entry_executed) ليست فيه، بينما
الصفحة تقول "كل صفقة أُغلقت". من دخلها كان بربح أو خسارة عند الانتهاء (قرار المالك 09/10)، فنقيس حجمها قبل فتح السجل.

R هنا **تقدير** من current_price (آخر سعر محفوظ بالصف، قد لا يكون سعر لحظة الانتهاء)؛ الصف بلا سعر يُعدّ بلا تقدير.
فريدة بقرار واحد لكل صفقة، بنفس decision_key.

    docker exec -i moshapi_backend python - < backend/diag_expired_entered.py
"""


def estimate_r(entry, stop, price):
    if price is None or not entry or not stop or entry == stop:
        return None
    return (float(price) - float(entry)) / (float(entry) - float(stop))


def summarize(rows):
    """rows = [(iso_week, r_or_None)] لكل قرار فريد ← {أسبوع: [عدد، بتقدير، رابح، خاسر، مجموع R]} مرتبة."""
    out = {}
    for wk, r in rows:
        b = out.setdefault(wk, [0, 0, 0, 0, 0.0])
        b[0] += 1
        if r is not None:
            b[1] += 1
            b[2] += 1 if r > 0 else 0
            b[3] += 0 if r > 0 else 1
            b[4] += r
    return dict(sorted(out.items()))


def main():
    from app.database import SessionLocal
    from app.models.signal import Signal, SignalStatus
    from app.services.decision_grouping import decision_key
    from app.services.quality_report import OUTCOME_FIX_DATE
    db = SessionLocal()
    rows = db.query(Signal).filter(Signal.status == SignalStatus.EXPIRED, Signal.entry_executed.isnot(None),
                                   Signal.created_at >= OUTCOME_FIX_DATE).order_by(Signal.created_at).all()
    uniq = {}
    for s in rows:
        uniq.setdefault(decision_key(s.market, s.timeframe, s.signal_type, s.entry_price), s)
    data = []
    for s in uniq.values():
        y, w, _ = s.created_at.isocalendar()
        data.append((f"{y}-W{w:02d}", estimate_r(s.entry_price, s.stop_loss, s.current_price)))
    table = summarize(data)
    print(f"تفعّلت ثم انتهت منذ {OUTCOME_FIX_DATE:%Y-%m-%d}: {len(rows)} صفاً ← {len(uniq)} صفقة فريدة\n")
    print(f"  {'الأسبوع':<10} {'عدد':>4} {'بتقدير':>6} {'رابح/خاسر':>10} {'مجموع R (تقدير)':>16}")
    for wk, b in table.items():
        print(f"  {wk:<10} {b[0]:>4} {b[1]:>6} {b[2]:>4}/{b[3]:<5} {b[4]:>+15.1f}R")
    tot = [sum(b[i] for b in table.values()) for i in range(5)]
    print(f"\n  المجموع: {tot[0]} صفقة، بتقدير {tot[1]}، {tot[2]} رابحة / {tot[3]} خاسرة، {tot[4]:+.1f}R (تقدير)")
    print("  للمقارنة: السجل العام 1022 صفقة، +299.53R (معاينة 30/10). للقراءة فقط — لا يغيّر شيئاً.")
    db.close()


if __name__ == "__main__":
    main()
