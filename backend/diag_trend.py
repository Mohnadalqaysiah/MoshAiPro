"""
diag_trend.py — تشخيص قراءة فقط: الصفقات عكس اتجاه 4h — نمنعها أم نقلبها؟ (2026-10-10)
=====================================================================================
تشخيص الذهب والفضة (diag_gold.py) أظهر أن الخسائر تتركّز في الصفقات عكس اتجاه
4h (EMA50). سؤال صاحب المنتج: بدل منعها (تقليل الإشارات)، هل نقلبها مع
الاتجاه فتربح؟ القلب ليس مضموناً: صفقة خسرت 1R لا يعني أن السعر واصل حتى
هدف المقلوبة (2-3R) — فنقيس بدل أن نفترض.

لكل رمز، على نفس الصفقات ونفس الشموع، ثلاثة سيناريوهات:
  1) الأساس: كما أُرسلت
  2) منع: حذف الصفقات عكس الاتجاه
  3) قلب: كل صفقة عكس الاتجاه تُستبدل بمرآتها — نفس الدخول، الاتجاه المعاكس،
     الستوب والأهداف معكوسة بنفس المسافات (نفس R)

الاتجاه: سعر 4h مقابل EMA50 وميلها لحظة الإشارة (UP/DOWN/FLAT).
المحاكاة بقواعد حلقة الرصد (diag_gold.simulate). المصادر بنفس قاعدة الحلقة:
الذهب والفضة شموع TV الفورية، وغيرهما yfinance (مرجع بناء مستوياتهما).

التشغيل:
  docker cp backend/diag_trend.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/diag_trend.py 2>/dev/null                      # الرموز الأساسية، 14 يوم
  docker exec moshapi_backend python /app/diag_trend.py XAUUSD,XAGUSD 14 2>/dev/null      # رموز محددة
"""
import sys, asyncio
sys.path.insert(0, "/app")

from datetime import datetime, timedelta, timezone
import pandas as pd

from app.database import SessionLocal
from app.models.signal import Signal, SignalStatus
from app.services.decision_grouping import group_unique_decisions
from diag_gold import simulate, TRUSTED_FROM

DEFAULT = ("XAUUSD,XAGUSD,XPTUSD,BTCUSD,ETHUSD,SOLUSD,BNBUSD,XRPUSD,ADAUSD,DOGEUSD,"
           "EURUSD,GBPUSD,USDJPY,USDCAD,AUDUSD,NZDUSD,GBPJPY,EURJPY,USOIL,NATGAS,COPPER")
SYMBOLS = [s.strip().upper() for s in (sys.argv[1] if len(sys.argv) > 1 else DEFAULT).split(",") if s.strip()]
DAYS = int(sys.argv[2]) if len(sys.argv) > 2 else 14
SPOT_TV = {"XAUUSD", "XAGUSD"}


def _norm(df):
    df = df.sort_values("ts").reset_index(drop=True)
    return df


async def _candles(sym):
    """(5m, 4h) — نفس قاعدة مرجع الحلقة."""
    if sym in SPOT_TV:
        from app.services.tv_price_feed import TV_SYMBOL_MAP, fetch_tv_history
        m5b = await fetch_tv_history(TV_SYMBOL_MAP[sym], "5m", bars=5000, timeout_s=40)
        await asyncio.sleep(1)
        h4b = await fetch_tv_history(TV_SYMBOL_MAP[sym], "4h", bars=400, timeout_s=30)
        if not m5b or not h4b:
            return None, None
        mk = lambda bars: pd.DataFrame([(b[0], b[2], b[3], b[4]) for b in bars],
                                       columns=["ts", "high", "low", "close"]).assign(
                                       ts=lambda d: pd.to_datetime(d.ts, unit="s", utc=True))
        return _norm(mk(m5b)), _norm(mk(h4b))
    import yfinance as yf
    from app.services.smart_data import _resolve_yf_symbol
    t = yf.Ticker(_resolve_yf_symbol(sym))
    m5 = t.history(period="60d", interval="5m", auto_adjust=True)
    h1 = t.history(period="180d", interval="1h", auto_adjust=True)
    if m5 is None or not len(m5) or h1 is None or not len(h1):
        return None, None
    m5 = pd.DataFrame({"ts": pd.to_datetime(m5.index, utc=True), "high": m5.High.values,
                       "low": m5.Low.values, "close": m5.Close.values}).dropna()
    h1.index = pd.to_datetime(h1.index, utc=True)
    h4 = h1.resample("4h").agg({"High": "max", "Low": "min", "Close": "last"}).dropna()
    h4 = pd.DataFrame({"ts": h4.index, "high": h4.High.values, "low": h4.Low.values, "close": h4.Close.values})
    return _norm(m5), _norm(h4)


def _stats(rs):
    rs = [r for r in rs if r is not None]
    if not rs:
        return "—"
    w = sum(1 for r in rs if r > 0)
    return f"{len(rs):3d} صفقة  {w:3d}ر/{len(rs)-w:3d}خ  {w*100/len(rs):5.1f}%  {sum(rs)/len(rs):+.2f}R  مجموع {sum(rs):+6.1f}R"


async def main():
    db = SessionLocal()
    since = max(TRUSTED_FROM, datetime.now(timezone.utc) - timedelta(days=DAYS))
    statuses = [SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT, SignalStatus.EXPIRED]
    rows = db.query(Signal).filter(func_upper_in(Signal.market, SYMBOLS),
                                   Signal.status.in_(statuses), Signal.created_at >= since).all()
    db.close()
    print(f"📊 منذ {since:%Y-%m-%d} — {len(SYMBOLS)} رمز\n")

    total = {"base": [], "with": [], "against": [], "neutral": [], "mirror": []}
    lines = []
    for sym in SYMBOLS:
        sigs = [s for s in rows if (s.market or "").upper() == sym]
        if not sigs:
            continue
        try:
            m5, h4 = await _candles(sym)
        except Exception as e:
            print(f"  ⚠️ {sym}: {type(e).__name__}: {e}")
            continue
        if m5 is None:
            print(f"  ⚠️ {sym}: لا شموع")
            continue
        h4["ema50"] = h4.close.ewm(span=50, adjust=False).mean()
        data = list(zip(m5.ts, m5.high.astype(float), m5.low.astype(float), m5.close.astype(float)))
        by_id = {s.id: s for s in sigs}
        per = {"base": [], "with": [], "against": [], "neutral": [], "mirror": []}

        for g in group_unique_decisions(sigs):
            s = by_id[g["id"]]
            created = s.created_at if s.created_at.tzinfo else s.created_at.replace(tzinfo=timezone.utc)
            if created < m5.ts.iloc[0]:
                continue
            exp = s.expires_at or (created + timedelta(hours=24))
            exp = exp if exp.tzinfo else exp.replace(tzinfo=timezone.utc)
            entry, sl = float(s.entry_price), float(s.stop_loss)
            tp1 = float(s.take_profit_1); tp2 = float(s.take_profit_2 or tp1)
            is_buy = (s.signal_type.value if hasattr(s.signal_type, "value") else s.signal_type) == "BUY"
            if not abs(entry - sl):
                continue
            r = simulate(data, created, exp, entry, sl, tp1, tp2, is_buy)[1]
            if r is None:          # لم يتفعّل أو لسا مفتوح — لا يدخل أي سيناريو
                continue
            e4 = h4[h4.ts < created].tail(6)
            trend = "FLAT"
            if len(e4) == 6:
                px, ema, slope = float(e4.close.iloc[-1]), float(e4.ema50.iloc[-1]), float(e4.ema50.iloc[-1] - e4.ema50.iloc[0])
                trend = "UP" if (px > ema and slope > 0) else "DOWN" if (px < ema and slope < 0) else "FLAT"
            per["base"].append(r)
            if trend == "FLAT":
                per["neutral"].append(r)
            elif (trend == "UP") == is_buy:
                per["with"].append(r)
            else:
                per["against"].append(r)
                # المرآة: نفس الدخول، الاتجاه المعاكس، نفس المسافات
                rm = simulate(data, created, exp, entry, 2 * entry - sl, 2 * entry - tp1,
                              2 * entry - tp2, not is_buy)[1]
                per["mirror"].append(rm)

        for k in total:
            total[k] += per[k]
        block = per["with"] + per["neutral"]
        flip = per["with"] + per["neutral"] + [x for x in per["mirror"] if x is not None]
        lines.append((sym, per, block, flip))
        await asyncio.sleep(1.0)

    for sym, per, block, flip in lines:
        print(f"── {sym}")
        print(f"   مع الاتجاه      {_stats(per['with'])}")
        print(f"   عكس الاتجاه     {_stats(per['against'])}")
        print(f"   محايد           {_stats(per['neutral'])}")
        print(f"   عكسها مقلوبة    {_stats(per['mirror'])}")
        print(f"   ▸ الأساس        {_stats(per['base'])}")
        print(f"   ▸ منع           {_stats(block)}")
        print(f"   ▸ قلب           {_stats(flip)}")

    print("\n" + "=" * 100)
    print("المجموع لكل الرموز")
    print(f"   مع الاتجاه      {_stats(total['with'])}")
    print(f"   عكس الاتجاه     {_stats(total['against'])}")
    print(f"   محايد           {_stats(total['neutral'])}")
    print(f"   عكسها مقلوبة    {_stats(total['mirror'])}")
    print(f"   ▸ الأساس        {_stats(total['base'])}")
    print(f"   ▸ منع           {_stats(total['with'] + total['neutral'])}")
    print(f"   ▸ قلب           {_stats(total['with'] + total['neutral'] + [x for x in total['mirror'] if x is not None])}")
    print("=" * 100)
    print("⚠️ محاكاة على الماضي لا وعد بالمستقبل. رمز بعينة < 10 مؤشر لا حكم.")


def func_upper_in(col, values):
    from sqlalchemy import func
    return func.upper(col).in_(values)


if __name__ == "__main__":
    asyncio.run(main())
