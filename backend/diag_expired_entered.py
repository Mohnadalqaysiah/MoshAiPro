"""
(2026-10-30) صفقات تفعّل دخولها ثم انتهت مدتها بلا هدف ولا وقف — هل تغيّر صورة سجل الأداء العام؟ للقراءة فقط.

سجل /results يقرأ closed_decisions (TP1/TP2/SL/BREAKEVEN)، فهذه الصفقات (status=EXPIRED مع entry_executed) ليست فيه، بينما
الصفحة تقول "كل صفقة أُغلقت". من دخلها كان بربح أو خسارة عند الانتهاء (قرار المالك 09/10)، فنقيس حجمها قبل فتح السجل.

R = إغلاق آخر شمعة 5m قبل انتهاء المدة (نفس قاعدة EXPIRED_PROFIT/LOSS بأداة "تحقق من الكل")، بمصادر شموع diag_target_profile:
الذهب والفضة TradingView الفوري، وغيرهما yfinance حتى 60 يوماً. current_price فارغ بهذه الصفوف (أول تشغيل 30/10: 0 من 70) فلا يصلح.
رمز بلا شموع (الخليج) أو صفقة أقدم من الشموع = "بلا قياس" ولا يُخمَّن. فريدة بقرار واحد لكل صفقة، بنفس decision_key.

    docker cp backend/diag_target_profile.py moshapi_backend:/app/
    docker cp backend/diag_expired_entered.py moshapi_backend:/app/
    docker exec moshapi_backend python diag_expired_entered.py 2>/dev/null
"""
import asyncio
from datetime import timedelta, timezone


def estimate_r(entry, stop, price):
    if price is None or not entry or not stop or entry == stop:
        return None
    return (float(price) - float(entry)) / (float(entry) - float(stop))


def last_close_before(data, start, end):
    """data = [(ts, high, low, close)] مرتبة. إغلاق آخر شمعة ضمن [start, end]، أو None."""
    out = None
    for ts, _, _, cl in data:
        if ts < start:
            continue
        if ts > end:
            break
        out = cl
    return out


def summarize(rows):
    """rows = [(iso_week, r_or_None)] لكل قرار فريد ← {أسبوع: [عدد، مقاس، رابح، خاسر، مجموع R]} مرتبة."""
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


def _utc(d):
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


async def main():
    from app.database import SessionLocal
    from app.models.signal import Signal, SignalStatus
    from app.services.decision_grouping import decision_key
    from app.services.quality_report import OUTCOME_FIX_DATE
    from diag_target_profile import _candles
    db = SessionLocal()
    rows = db.query(Signal).filter(Signal.status == SignalStatus.EXPIRED, Signal.entry_executed.isnot(None),
                                   Signal.created_at >= OUTCOME_FIX_DATE).order_by(Signal.created_at).all()
    db.close()
    uniq = {}
    for s in rows:
        uniq.setdefault(decision_key(s.market, s.timeframe, s.signal_type, s.entry_price), s)
    cache, no_candles = {}, set()
    data = []
    for s in uniq.values():
        sym = (s.market or "").upper()
        if sym not in cache:
            try:
                m5 = await _candles(sym)
            except Exception:
                m5 = None
            cache[sym] = list(zip(m5.ts, m5.high.astype(float), m5.low.astype(float), m5.close.astype(float))) \
                if m5 is not None and len(m5) else None
            await asyncio.sleep(1.0)
        y, w, _ = s.created_at.isocalendar()
        created = _utc(s.created_at)
        end = _utc(s.expires_at) if s.expires_at else created + timedelta(hours=24)
        px = last_close_before(cache[sym], _utc(s.entry_executed), end) if cache[sym] else None
        if cache[sym] is None:
            no_candles.add(sym)
        data.append((f"{y}-W{w:02d}", estimate_r(s.entry_price, s.stop_loss, px)))
    table = summarize(data)
    print(f"تفعّلت ثم انتهت منذ {OUTCOME_FIX_DATE:%Y-%m-%d}: {len(rows)} صفاً ← {len(uniq)} صفقة فريدة\n")
    print(f"  {'الأسبوع':<10} {'عدد':>4} {'مقاس':>6} {'رابح/خاسر':>10} {'مجموع R':>10}")
    for wk, b in table.items():
        print(f"  {wk:<10} {b[0]:>4} {b[1]:>6} {b[2]:>4}/{b[3]:<5} {b[4]:>+9.1f}R")
    tot = [sum(b[i] for b in table.values()) for i in range(5)]
    avg = tot[4] / tot[1] if tot[1] else 0.0
    print(f"\n  المجموع: {tot[0]} صفقة، مقاس منها {tot[1]}: {tot[2]} رابحة / {tot[3]} خاسرة، {tot[4]:+.1f}R (متوسط {avg:+.2f}R)")
    if no_candles:
        print(f"  بلا شموع: {', '.join(sorted(no_candles))}")
    print("  للمقارنة: السجل العام 1022 صفقة، +299.53R (معاينة 30/10). للقراءة فقط — لا يغيّر شيئاً.")


if __name__ == "__main__":
    asyncio.run(main())
