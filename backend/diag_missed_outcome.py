"""
(2026-10-16) تشخيص للقراءة فقط: لماذا لم تسجّل حلقة الرصد نتيجة صفقة بلغت وقفها/هدفها (مثال NAS100 #5914)؟

يطبع: بيانات الصفقة (الإنشاء، المدة، تفعيل الدخول، الحالة)، ثم يقارن مصدري السعر اللذين تستخدمهما الحلقة:
  - السعر اللحظي: TradingView إن كان الرمز بـTV_SYMBOL_MAP (لـNAS100 = NASDAQ:NDX — المؤشر النقدي)
  - شموع المشي الزمني: get_ohlcv 5m (لـNAS100 = yfinance NQ=F — العقد الآجل، مرجع بناء المستويات)
وأعلى/أدنى سعر خلال مدة الصفقة بكل مصدر، ومتى لُمس الدخول والوقف والهدف بكل منهما. لا يكتب شيئاً.

    docker exec moshapi_backend python diag_missed_outcome.py [رقم الصفقة=5914]
"""
import asyncio
import sys
from datetime import timezone

from app.database import SessionLocal
from app.models.signal import Signal

SID = int(sys.argv[1]) if len(sys.argv) > 1 else 5914


def _utc(d):
    return d if d is None or d.tzinfo else d.replace(tzinfo=timezone.utc)


def _touches(bars, s, label):
    """bars: [(epoch, high, low)] صاعداً. يطبع أول لمس للدخول ثم الوقف/الأهداف بعده."""
    buy = s.signal_type.value == "BUY"
    entry, sl, tp1, tp2 = s.entry_price, s.stop_loss, s.take_profit_1, s.take_profit_2
    t0, t1 = _utc(s.created_at).timestamp(), _utc(s.expires_at).timestamp()
    w = [b for b in bars if t0 - 300 <= b[0] <= t1]
    if not w:
        print(f"  {label}: لا شموع ضمن مدة الصفقة")
        return
    hi, lo = max(b[1] for b in w), min(b[2] for b in w)
    print(f"  {label}: {len(w)} شمعة | أعلى {hi} | أدنى {lo}")
    from datetime import datetime
    fmt = lambda e: datetime.fromtimestamp(e, timezone.utc).strftime("%m-%d %H:%M")
    hit_entry = next((b for b in w if (b[2] <= entry if buy else b[1] >= entry)), None)
    print(f"     الدخول {entry}: {'لُمس ' + fmt(hit_entry[0]) if hit_entry else 'لم يُلمس'}")
    after = [b for b in w if hit_entry and b[0] >= hit_entry[0]]
    for name, lvl, cond in (("الوقف", sl, (lambda b: b[2] <= sl) if buy else (lambda b: b[1] >= sl)),
                            ("TP1", tp1, (lambda b: b[1] >= tp1) if buy else (lambda b: b[2] <= tp1)),
                            ("TP2", tp2, (lambda b: b[1] >= tp2) if buy else (lambda b: b[2] <= tp2))):
        h = next((b for b in after if cond(b)), None)
        print(f"     {name} {lvl}: {'لُمس ' + fmt(h[0]) if h else 'لم يُلمس'}")


async def main():
    db = SessionLocal()
    s = db.query(Signal).get(SID)
    if not s:
        print("الصفقة غير موجودة")
        return
    sym = s.market.upper()
    print(f"#{s.id} {sym} {s.timeframe} {s.signal_type.value} | الحالة {s.status.value} | تحقق يدوي {s.outcome_verified}")
    print(f"  دخول {s.entry_price} | وقف {s.stop_loss} | TP1 {s.take_profit_1} | TP2 {s.take_profit_2}")
    print(f"  أُنشئت {_utc(s.created_at)} | تنتهي {_utc(s.expires_at)}")
    print(f"  تفعيل الدخول (entry_executed) {_utc(s.entry_executed)} | الخروج {_utc(s.exit_executed)} | آخر سعر مرصود {s.current_price}")

    from app.services.tv_price_feed import TV_SYMBOL_MAP, fetch_tv_history, tv_feed
    from app.services.smart_data import smart_data
    tv_sym = TV_SYMBOL_MAP.get(sym)
    print(f"\nمصدر السعر اللحظي بالحلقة: {'TradingView ' + tv_sym if tv_sym else 'smart_data (yfinance/Finnhub)'}")
    print(f"السوق مفتوح الآن بحسب المنصة: {smart_data.is_market_open(sym)}")

    tv_bars = []
    if tv_sym:
        raw = await fetch_tv_history(tv_sym, "5m", bars=600)
        tv_bars = sorted((float(b[0]), float(b[2]), float(b[3])) for b in (raw or []))
        live = tv_feed.get_price_sync(sym)
        print(f"TV الآن: آخر إغلاق شمعة {raw[-1][4] if raw else '—'} | كاش السعر اللحظي {live}")
    df = await smart_data.get_ohlcv(sym, "5m", bars=600)
    yf_bars = []
    if df is not None and len(df):
        import pandas as pd
        col = next((c for c in ("datetime", "timestamp", "Datetime", "Date", "index") if c in df.columns), None)
        ts = pd.to_datetime(df[col] if col else df.index, utc=True)
        yf_bars = sorted(zip((t.timestamp() for t in ts), df["high"].astype(float), df["low"].astype(float)))
        print(f"get_ohlcv الآن: آخر إغلاق {float(df['close'].iloc[-1])}")
    if tv_bars and yf_bars:
        print(f"فرق المصدرين الآن (get_ohlcv − TV): {yf_bars[-1][1] - tv_bars[-1][1]:+.2f} تقريباً (أعلى آخر شمعة)")

    print("\nخلال مدة الصفقة:")
    if tv_bars:
        _touches(tv_bars, s, f"TV {tv_sym}")
    _touches(yf_bars, s, "get_ohlcv (مرجع المستويات)")
    db.close()


if __name__ == "__main__":
    asyncio.run(main())
