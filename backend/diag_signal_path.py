"""
diag_signal_path.py — (2026-11-12) لماذا لم تُحسم صفقة؟ مسار السعر شمعة بشمعة لإشارة واحدة. قراءة فقط.

سؤال المالك عن #10330 (XAUUSD 1h بيع): "حققت كل الأهداف ولم تُسجَّل". يطبع:
  - الصف كاملاً (الأهداف، المدة، الدخول المنفّذ، المستخدم، هل هي بث عام أم تنبيه مراقبة خاص)
  - على مرجع الحكم الفعلي (TradingView الفوري للمعادن، كأداة التحقق وحلقة الرصد): متى لُمس الدخول، وأدنى/أعلى سعر بعده ومتى،
    وأقرب مسافة للهدف الأول والوقف
  - نفس الشيء على العقود الآجلة (yfinance) للمقارنة — فرق المرجعين يفسّر "وصل عندي ولم يصل عند المنصة"

  docker exec -i moshapi_backend python - 10330 < backend/diag_signal_path.py
"""
import asyncio
import sys
from datetime import timezone

sys.path.insert(0, "/app")


def _utc(d):
    return d if d is None or d.tzinfo else d.replace(tzinfo=timezone.utc)


def walk(rows, created, expires, entry, sl, tp1, tp2, tp3, is_buy):
    """rows: (ts UTC، أعلى، أدنى). يعيد ملخص المسار بنفس قاعدة لمس الدخول (lo <= entry <= hi)."""
    entry_ts, best, best_ts, worst, worst_ts, first = None, None, None, None, None, {}
    for ts, hi, lo in rows:
        if ts < created or (expires and ts > expires):
            continue
        if entry_ts is None:
            if not (lo <= entry <= hi):
                continue
            entry_ts = ts
        fav, adv = (hi, lo) if is_buy else (lo, hi)
        if best is None or (fav > best if is_buy else fav < best):
            best, best_ts = fav, ts
        if worst is None or (adv < worst if is_buy else adv > worst):
            worst, worst_ts = adv, ts
        for name, lvl, good in (("الوقف", sl, False), ("الهدف 1", tp1, True), ("الهدف 2", tp2, True), ("الهدف 3", tp3, True)):
            if lvl and name not in first:
                hit = (hi >= lvl if is_buy else lo <= lvl) if good else (lo <= lvl if is_buy else hi >= lvl)
                if hit:
                    first[name] = ts
    return {"entry_ts": entry_ts, "best": best, "best_ts": best_ts, "worst": worst, "worst_ts": worst_ts, "first": first}


def _print(name, res, entry, sl, tp1, is_buy):
    print(f"\n── {name} ──")
    if res is None:
        print("  لا شموع")
        return
    if res["entry_ts"] is None:
        print("  الدخول لم يُلمس ضمن المدة — الصفقة لم تُفتح")
        return
    risk = abs(entry - sl)
    to_r = (lambda p: (p - entry) / risk) if is_buy else (lambda p: (entry - p) / risk)
    print(f"  لُمس الدخول: {res['entry_ts']:%m-%d %H:%M} UTC")
    print(f"  أفضل سعر بعده: {res['best']:.2f} ({to_r(res['best']):+.2f}R) عند {res['best_ts']:%m-%d %H:%M}"
          f" — الهدف 1 {tp1:.2f} يبعد عنه {abs(res['best'] - tp1):.2f}")
    print(f"  أسوأ سعر بعده: {res['worst']:.2f} ({to_r(res['worst']):+.2f}R) عند {res['worst_ts']:%m-%d %H:%M}"
          f" — الوقف {sl:.2f} يبعد عنه {abs(res['worst'] - sl):.2f}")
    if res["first"]:
        for k, v in sorted(res["first"].items(), key=lambda x: x[1]):
            print(f"  أول لمس {k}: {v:%m-%d %H:%M} UTC")
    else:
        print("  لم يُلمس أي هدف ولا الوقف")


async def main(sid):
    import pandas as pd
    from app.database import SessionLocal
    from app.models.signal import Signal
    from app.models.user import User
    db = SessionLocal()
    s = db.query(Signal).filter(Signal.id == sid).first()
    if not s:
        print("لا توجد إشارة بهذا الرقم")
        return
    u = db.query(User).filter(User.id == s.user_id).first()
    db.close()
    is_buy = getattr(s.signal_type, "value", s.signal_type) == "BUY"
    entry, sl, tp1 = float(s.entry_price), float(s.stop_loss), float(s.take_profit_1)
    tp2 = float(s.take_profit_2) if s.take_profit_2 else None
    tp3 = float(s.take_profit_3) if s.take_profit_3 else None
    created, expires = _utc(s.created_at), _utc(s.expires_at)
    print(f"#{s.id} {s.market} {s.timeframe} {'شراء' if is_buy else 'بيع'} — الحالة {getattr(s.status, 'value', s.status)}")
    print(f"  الدخول {entry} | الوقف {sl} | الهدف 1 {tp1} | الهدف 2 {tp2} | الهدف 3 {tp3}")
    print(f"  أُنشئت {created:%m-%d %H:%M} UTC | تنتهي {expires:%m-%d %H:%M} UTC" if expires else f"  أُنشئت {created}")
    print(f"  المستخدم: {u.email if u else s.user_id} | بث عام: {'نعم' if s.broadcast_sent else 'لا — تنبيه مراقبة خاص بصاحبه أو لم يُبث'}"
          f" | دخول منفّذ مسجّل: {s.entry_executed} | آخر سعر مرصود: {s.current_price}")

    spot = None
    try:
        from app.services.tv_price_feed import TV_SYMBOL_MAP, fetch_tv_history
        tv = TV_SYMBOL_MAP.get(s.market.upper())
        if tv:
            bars = await fetch_tv_history(tv, "5m", bars=1000)
            spot = [(pd.Timestamp(b[0], unit="s", tz="UTC").to_pydatetime(), float(b[2]), float(b[3])) for b in bars or []]
            print(f"\n  المرجع الفوري: {tv} — {len(spot)} شمعة 5m")
    except Exception as e:
        print(f"  تعذّر TradingView: {e}")
    _print("مرجع الحكم (الفوري — كأداة التحقق وحلقة الرصد)",
           walk(spot, created, expires, entry, sl, tp1, tp2, tp3, is_buy) if spot else None, entry, sl, tp1, is_buy)

    fut = None
    try:
        from app.services.smart_data import smart_data
        df = await smart_data.get_ohlcv(s.market, "5m", bars=1000)
        col = next((c for c in ("datetime", "time", "timestamp") if c in df.columns), None)
        times = pd.DatetimeIndex(pd.to_datetime(df[col] if col else df.index))
        times = times.tz_convert("UTC") if times.tz is not None else times.tz_localize("UTC")
        fut = [(t.to_pydatetime(), float(h), float(lo)) for t, h, lo in zip(times, df["high"], df["low"])]
    except Exception as e:
        print(f"  تعذّر المرجع الآخر: {e}")
    _print("المرجع الآخر (yfinance — للذهب عقود آجلة أعلى من الفوري بالفارق)",
           walk(fut, created, expires, entry, sl, tp1, tp2, tp3, is_buy) if fut else None, entry, sl, tp1, is_buy)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 0))
