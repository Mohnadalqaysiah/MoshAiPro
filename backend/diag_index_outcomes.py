"""
(2026-10-16) تحقق للقراءة فقط: نتائج المؤشرات الأمريكية (NAS100/US30/SP500) المسجّلة قبل إصلاح مصدر السعر.

قبل 16/10 كانت حلقة الرصد تقيس السعر اللحظي بالمؤشر النقدي (NDX/DJI/SPX) بينما المستويات من العقد الآجل — فرق ~196
نقطة على NAS100 (diag_missed_outcome 5914). هنا يُعاد المشي على شموع العقد الآجل 15m (نفس مرجع المستويات، ~60 يوماً):
من الإنشاء حتى انتهاء المدة، الدخول أولاً ثم أول مستوى يُلمس (الوقف أولاً إن لُمس هو وهدف بنفس الشمعة = "غامض").
يقارن بالنتيجة المسجّلة لكل قرار فريد. لا يكتب شيئاً — التصحيح قرار المالك بعد رؤية النتيجة.

    docker exec moshapi_backend python diag_index_outcomes.py
"""
import asyncio
from datetime import timezone

from app.database import SessionLocal
from app.models.signal import Signal, SignalStatus
from app.services.decision_grouping import verified_unique_decisions
from app.services.quality_report import _r_multiple, OUTCOME_FIX_DATE

INDICES = ["NAS100", "US30", "SP500"]


def _utc(d):
    return d if d is None or d.tzinfo else d.replace(tzinfo=timezone.utc)


def walk(bars, s):
    buy = s.signal_type.value == "BUY"
    e, sl, t1, t2 = s.entry_price, s.stop_loss, s.take_profit_1, s.take_profit_2
    t0, tx = _utc(s.created_at).timestamp(), _utc(s.expires_at).timestamp()
    w = [b for b in bars if t0 - 900 < b[0] <= tx]
    if not w:
        return "NO_DATA"
    started = False
    tp1 = False
    for ts, hi, lo in w:
        if not started:
            if (lo <= e) if buy else (hi >= e):
                started = True
            else:
                continue
        hit_sl = (lo <= sl) if buy else (hi >= sl)
        hit_t2 = (hi >= t2) if buy else (lo <= t2)
        hit_t1 = (hi >= t1) if buy else (lo <= t1)
        if hit_sl and (hit_t1 or hit_t2) and not tp1:
            return "AMBIGUOUS"
        if hit_sl:
            return "TP1_HIT" if tp1 else "SL_HIT"
        if hit_t2:
            return "TP2_HIT"
        if hit_t1:
            tp1 = True
    if not started:
        return "NOT_TRIGGERED"
    return "TP1_HIT" if tp1 else "EXPIRED"


async def main():
    from app.services.smart_data import smart_data
    import pandas as pd
    db = SessionLocal()
    rows = db.query(Signal).filter(
        Signal.market.in_(INDICES),
        Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT]),
        Signal.created_at >= OUTCOME_FIX_DATE,
    ).all()
    by_id = {s.id: s for s in rows}
    decs = sorted(verified_unique_decisions(rows), key=lambda d: _utc(d["created_at"]))
    bars = {}
    for sym in INDICES:
        df = await smart_data.get_ohlcv(sym, "15m", bars=4000)
        if df is None or not len(df):
            bars[sym] = []
            continue
        col = next((c for c in ("datetime", "timestamp", "Datetime", "Date") if c in df.columns), None)
        ts = pd.to_datetime(df[col] if col else df.index, utc=True)
        bars[sym] = sorted(zip((t.timestamp() for t in ts), df["high"].astype(float), df["low"].astype(float)))
        if bars[sym]:
            from datetime import datetime
            print(f"{sym}: شموع 15m من {datetime.fromtimestamp(bars[sym][0][0], timezone.utc):%m-%d} "
                  f"إلى {datetime.fromtimestamp(bars[sym][-1][0], timezone.utc):%m-%d}")

    same = diff = nodata = 0
    r_now = r_new = 0.0
    lines = []
    for d in decs:
        s = by_id.get(d["id"])
        if not s:
            continue
        got = walk(bars.get(s.market, []), s)
        rec = d["status"]
        rn = _r_multiple(s.entry_price, s.stop_loss, s.take_profit_1, s.take_profit_2, rec) or 0.0
        if got in ("NO_DATA", "AMBIGUOUS"):
            nodata += 1
            continue
        rg = _r_multiple(s.entry_price, s.stop_loss, s.take_profit_1, s.take_profit_2, got)
        rg = 0.0 if rg is None else rg      # لم يتفعّل/انتهى بلا نتيجة = لا يُحسب (0)
        r_now += rn
        r_new += rg
        if got == rec:
            same += 1
        else:
            diff += 1
            lines.append(f"  #{d['id']:<5} {s.market:<7} {s.timeframe:<4} {s.signal_type.value:<4} {_utc(s.created_at):%m-%d %H:%M} | "
                         f"مسجّل {rec:<8} ({rn:+.2f}R) ← الشموع: {got:<13} ({rg:+.2f}R) | صفوف {len(d.get('row_ids') or [1])}")
    print(f"\nقرارات مغلقة للمؤشرات منذ {OUTCOME_FIX_DATE:%m-%d}: {len(decs)}")
    print(f"  تطابقت مع الشموع: {same} | خالفت: {diff} | بلا بيانات أو غامضة: {nodata}")
    print(f"  مجموع R (المقارَنة فقط): المسجّل {r_now:+.2f}R ← حسب الشموع {r_new:+.2f}R")
    if lines:
        print("\nالمخالفة:")
        print("\n".join(lines))
    db.close()


if __name__ == "__main__":
    asyncio.run(main())
