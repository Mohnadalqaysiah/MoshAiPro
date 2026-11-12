"""
diag_metal_levels.py — (2026-11-12، بعد #10330) كم إشارة ذهب/فضة خرجت بأسعار العقد الآجل بدل الفوري؟ قراءة فقط.

لا تُحفظ مصدر السعر مع الإشارة، فالكشف بالمقارنة: لكل إشارة نأخذ السعر الفوري (OANDA، TradingView) والآجل (GC=F/SI=F) لحظة إنشائها
(إغلاق شمعة الساعة التي أُنشئت فيها). الدخول الصحيح قريب من الفوري؛ الدخول غير المحوّل قريب من الآجل. "آجل" = أقرب للآجل
بأكثر من MARGIN وفارق المرجعين وقتها أكبر من MIN_BASIS (حين يكون الفارق صغيراً لا يمكن التمييز — ولا ضرر يُذكر).

  docker exec -i moshapi_backend python - < backend/diag_metal_levels.py
"""
import asyncio
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "/app")

SINCE = datetime(2026, 9, 16, tzinfo=timezone.utc)
SYMS = {"XAUUSD": ("OANDA:XAUUSD", 3.0, 2.0), "XAGUSD": ("OANDA:XAGUSD", 0.15, 0.08)}   # (TV، أقل فارق، هامش)


def classify(entry, spot, fut, min_basis, margin):
    """'آجل' / 'فوري' / 'غير محدد' (الفارق صغير) / 'لا بيانات'."""
    if spot is None or fut is None:
        return "لا بيانات"
    if abs(fut - spot) < min_basis:
        return "غير محدد"
    ds, df = abs(entry - spot), abs(entry - fut)
    if df + margin < ds:
        return "آجل"
    if ds + margin < df:
        return "فوري"
    return "غير محدد"


def price_at(series, t):
    """إغلاق آخر شمعة ساعة بدأت قبل t أو عنده."""
    best = None
    for ts, close in series:
        if ts <= t:
            best = close
        else:
            break
    return best


async def main():
    import pandas as pd
    from app.database import SessionLocal
    from app.models.signal import Signal
    from app.services.decision_grouping import group_unique_decisions, merge_reissued
    from app.services.smart_data import smart_data
    from app.services.tv_price_feed import fetch_tv_history

    db = SessionLocal()
    rows = db.query(Signal).filter(Signal.market.in_(list(SYMS)), Signal.created_at >= SINCE).all()
    db.close()
    by_id = {s.id: s for s in rows}
    decs = merge_reissued(group_unique_decisions(rows))
    print(f"قرارات ذهب/فضة منذ {SINCE:%Y-%m-%d}: {len(decs)}\n")

    for sym, (tv, min_basis, margin) in SYMS.items():
        bars = await fetch_tv_history(tv, "1h", bars=2000)
        spot = sorted((pd.Timestamp(b[0], unit="s", tz="UTC").to_pydatetime(), float(b[4])) for b in bars or [])
        df = await smart_data.get_ohlcv(sym, "1h", bars=2000)
        col = next((c for c in ("datetime", "time", "timestamp") if c in df.columns), None)
        times = pd.DatetimeIndex(pd.to_datetime(df[col] if col else df.index))
        times = times.tz_convert("UTC") if times.tz is not None else times.tz_localize("UTC")
        fut = sorted(zip([t.to_pydatetime() for t in times], [float(c) for c in df["close"]]))
        first_spot = spot[0][0] if spot else None
        print(f"══ {sym} — الفوري متاح من {first_spot:%Y-%m-%d} والآجل من {fut[0][0]:%Y-%m-%d} ══" if spot and fut else f"══ {sym} — بيانات ناقصة ══")
        counts, by_status, by_week, examples = Counter(), defaultdict(Counter), defaultdict(Counter), []
        for d in decs:
            if (d["market"] or "").upper() != sym:
                continue
            s = by_id.get(d["id"])
            t = s.created_at if s.created_at.tzinfo else s.created_at.replace(tzinfo=timezone.utc)
            sp, fu = price_at(spot, t), price_at(fut, t)
            c = classify(float(s.entry_price), sp, fu, min_basis, margin)
            st = getattr(s.status, "value", s.status)
            counts[c] += 1
            by_status[c][st] += 1
            by_week[t.isocalendar()[:2]][c] += 1
            if c == "آجل" and len(examples) < 8:
                examples.append(f"    #{s.id} {t:%m-%d %H:%M} {getattr(s.signal_type, 'value', s.signal_type)} دخول {s.entry_price:.2f}"
                                f" | فوري {sp:.2f} | آجل {fu:.2f} | {st}")
        total = sum(counts.values())
        for c in ("فوري", "آجل", "غير محدد", "لا بيانات"):
            if counts[c]:
                print(f"  {c:<9} {counts[c]:>4} ({counts[c] / total * 100:.0f}%) — النتائج: "
                      + "، ".join(f"{k} {v}" for k, v in by_status[c].most_common()))
        print("  أسبوعياً (آجل / الكل):  " + "  ".join(
            f"W{w[1]} {by_week[w]['آجل']}/{sum(by_week[w].values())}" for w in sorted(by_week)))
        if examples:
            print("  أمثلة:")
            print("\n".join(examples))
        print()
    print("قراءة: 'آجل' = خرجت بأسعار العقد الآجل (لا يراها العميل بـMT5). أغلبها لا يلمس دخوله على الفوري فلا يدخل الإحصاء (EXPIRED)،")
    print("أي أن الضرر الأساسي على العميل (سعر خاطئ) وعلى عدد صفقات الذهب المحسوبة، لا تضخيم للنتائج. ما قبل توفر الفوري (TV ~2000 ساعة) 'لا بيانات'.")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(main())
