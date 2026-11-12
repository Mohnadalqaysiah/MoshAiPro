"""
diag_entry_mode.py — (2026-11-12) محاكاة للقراءة فقط: الدخول بأمر معلّق (القاعدة الحالية) مقابل الدخول بسعر السوق لحظة الإشارة.

سؤال المالك بعد #10330 (بيع، الدخول 3960.33، اقترب السعر الفوري لمسافة 1$ ثم نزل 100$ — لم تُحسب، وهو دخل بسعر السوق وربح):
هل نحسب كل الإشارات كأن العميل دخل بسعر السوق لحظة وصولها؟ نفس الإشارات ونفس الوقف والأهداف بالسعر، على شموع 5m نفسها:

  معلّق: تبدأ حين يلمس السعر الدخول (lo ≤ الدخول ≤ hi)، كحلقة الرصد اليوم.
  سوق:   تبدأ بسعر إغلاق آخر شمعة 5m عند لحظة الإشارة. R بمخاطرتها هي (|سعر السوق − الوقف|).
         تُستبعد وتُعدّ: "غير صالحة" إن كان السعر تجاوز الوقف، و"متأخرة" إن كان تجاوز الهدف الأول.
المحاسبة واحدة للطريقتين (مقياس المنصة): أعلى هدف بلغته الصفقة، أو الوقف (الوقف أولاً إن لُمسا بنفس الشمعة)؛ عند انتهاء المدة
بلا هدف ولا وقف = إغلاق آخر شمعة. المفتوحة الآن مستبعدة.

⚠️ الفخ الذي تكشفه المقارنة: الصفقة التي اقتربت من الدخول ثم ارتدت تبدو رابحة "بسعر السوق" لأن السعر ارتد لصالحها — والعكس:
صفقات كان أمرها المعلّق سيعطي دخولاً أفضل. لذلك تُعرض المجموعة الثلاث منفصلة: المشتركة، والتي يفتحها السوق وحده، والمعلّق وحده.

  docker exec -i moshapi_backend python - [تاريخ البداية=2026-10-14] < backend/diag_entry_mode.py 2>/dev/null
"""
import asyncio
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "/app")

START = datetime(2026, 10, 14, tzinfo=timezone.utc)   # سقف الهدف الأول (14/10) — مستويات قابلة للمقارنة
BAR = timedelta(minutes=5)


def _targets(tp1, tp2, tp3, is_buy):
    """الأهداف المتاحة مرتبة بالبعد في اتجاه الصفقة، بلا تكرار."""
    sgn = 1 if is_buy else -1
    out = []
    for t in (tp1, tp2, tp3):
        if t and all(abs(t - x) > 1e-9 for x in out):
            out.append(float(t))
    return sorted(out, key=lambda t: sgn * t)


def simulate(rows, created, end_ts, entry, sl, tps, is_buy, mode, now=None):
    """rows: (ts، أعلى، أدنى، إغلاق) مرتبة. يعيد (R، الحالة): الحالة traded / not_triggered / invalid / late / open."""
    now = now or datetime.now(timezone.utc)
    sgn = 1 if is_buy else -1
    if mode == "market":
        # سعر السوق = إغلاق آخر شمعة **أُغلقت** قبل الإشارة (الشمعة التي بدأت قبلها وتُغلق بعدها تحمل معلومة من المستقبل)
        before = [r for r in rows if r[0] + BAR <= created]
        if not before:
            return None, "no_data"
        e = float(before[-1][3])
        if sgn * (e - sl) <= 0:
            return None, "invalid"
        if tps and sgn * (e - tps[0]) >= 0:
            return None, "late"
        path = [r for r in rows if created <= r[0] <= end_ts]          # نفس بداية رصد المعلّق (ts ≥ الإنشاء)
    else:
        e = float(entry)
        path, started = [], False
        for r in rows:
            ts, hi, lo, _ = r
            if ts < created:
                continue
            if ts > end_ts:
                break
            if not started:
                if not (lo <= e <= hi):
                    continue
                started = True
            path.append(r)
        if not started:
            return None, "not_triggered"
    risk = abs(e - sl)
    if not risk or not path:
        return None, "open" if end_ts > now else "no_data"
    best = None
    for ts, hi, lo, cl in path:
        if (lo <= sl) if is_buy else (hi >= sl):
            return ((sgn * (best - e) / risk) if best is not None else -1.0), "traded"
        for t in tps:
            if ((hi >= t) if is_buy else (lo <= t)) and (best is None or sgn * (t - best) > 0):
                best = t
        if tps and best == tps[-1]:
            return sgn * (best - e) / risk, "traded"
    if end_ts > now:
        return None, "open"
    if best is not None:
        return sgn * (best - e) / risk, "traded"
    return sgn * (float(path[-1][3]) - e) / risk, "traded"


def _line(name, rs):
    if not rs:
        return f"  {name:<34} —"
    w = sum(1 for r in rs if r > 0.001)
    return f"  {name:<34} {len(rs):>4} | ربح {w / len(rs) * 100:4.0f}% | مجموع {sum(rs):+7.1f}R | متوسط {sum(rs) / len(rs):+.2f}R"


async def main(start):
    import pandas as pd
    from app.database import SessionLocal
    from app.models.market_config import MarketConfig
    from app.models.signal import Signal, SignalStatus
    from app.services.decision_grouping import group_unique_decisions, merge_reissued
    from app.services.weekly_markets import market_group
    import diag_target_profile as TP

    db = SessionLocal()
    cat = {r[0].upper(): (r[1] or "") for r in db.query(MarketConfig.symbol, MarketConfig.category).all()}
    rows = db.query(Signal).filter(
        Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT, SignalStatus.EXPIRED,
                           SignalStatus.BREAKEVEN]), Signal.created_at >= start).all()
    db.close()
    by_id = {s.id: s for s in rows}
    decs = merge_reissued(group_unique_decisions(rows))
    symbols = sorted({(d["market"] or "").upper() for d in decs})
    print(f"📊 منذ {start:%Y-%m-%d}: {len(decs)} قرار على {len(symbols)} رمز — المحاكاة جارية...\n")

    res = []          # (رمز، مجموعة، أسبوع، R معلّق أو None، حالته، R سوق أو None، حالته)
    skipped = []
    for sym in symbols:
        try:
            df = await TP._candles(sym)
        except Exception as e:
            skipped.append(f"{sym} ({type(e).__name__})")
            continue
        if df is None or not len(df):
            skipped.append(sym)
            continue
        candles = [(t.to_pydatetime(), float(h), float(lo), float(c)) for t, h, lo, c in zip(df.ts, df.high, df.low, df.close)]
        first = candles[0][0]
        for d in [x for x in decs if (x["market"] or "").upper() == sym]:
            s = by_id.get(d["id"])
            created = s.created_at if s.created_at.tzinfo else s.created_at.replace(tzinfo=timezone.utc)
            end = s.expires_at if s.expires_at and s.expires_at.tzinfo else (
                s.expires_at.replace(tzinfo=timezone.utc) if s.expires_at else None)
            if not end or created < first:
                continue
            is_buy = getattr(s.signal_type, "value", s.signal_type) == "BUY"
            tps = _targets(s.take_profit_1, s.take_profit_2, s.take_profit_3, is_buy)
            rl, sl_ = simulate(candles, created, end, float(s.entry_price), float(s.stop_loss), tps, is_buy, "limit")
            rm, sm = simulate(candles, created, end, float(s.entry_price), float(s.stop_loss), tps, is_buy, "market")
            res.append((sym, market_group(sym, cat.get(sym, "")), created.isocalendar()[:2], rl, sl_, rm, sm))
        await asyncio.sleep(1.0)

    lim = [x[3] for x in res if x[4] == "traded"]
    mkt = [x[5] for x in res if x[6] == "traded"]
    both = [x for x in res if x[4] == "traded" and x[6] == "traded"]
    only_m = [x for x in res if x[4] == "not_triggered" and x[6] == "traded"]
    only_l = [x for x in res if x[4] == "traded" and x[6] in ("late", "invalid")]
    states = defaultdict(int)
    for x in res:
        states[("معلّق", x[4])] += 1
        states[("سوق", x[6])] += 1

    print("══ الإجمالي ══")
    print(_line("معلّق (القاعدة الحالية)", lim))
    print(_line("سعر السوق لحظة الإشارة", mkt))
    print(f"  معلّق لم يتفعّل: {states[('معلّق', 'not_triggered')]} | سوق: متأخرة (تجاوزت الهدف 1) {states[('سوق', 'late')]}"
          f"، غير صالحة (تجاوزت الوقف) {states[('سوق', 'invalid')]} | مفتوحة الآن (مستبعدة) {states[('معلّق', 'open')]}")
    print("\n══ من أين يأتي الفرق ══")
    print(_line("المشتركة — معلّق", [x[3] for x in both]))
    print(_line("المشتركة — سوق", [x[5] for x in both]))
    print(_line("يفتحها السوق وحده (معلّق لم يتفعّل)", [x[5] for x in only_m]))
    print(_line("يفتحها المعلّق وحده (سوق متأخر/غير صالح)", [x[3] for x in only_l]))

    print("\n══ حسب السوق (المجموع: معلّق ← سوق) ══")
    for g in sorted({x[1] for x in res}):
        a = [x[3] for x in res if x[1] == g and x[4] == "traded"]
        b = [x[5] for x in res if x[1] == g and x[6] == "traded"]
        print(f"  {g:<8} معلّق {len(a):>3} {sum(a):+6.1f}R  ←  سوق {len(b):>3} {sum(b):+6.1f}R")
    print("\n══ أسبوعياً (المجموع: معلّق ← سوق) ══")
    for w in sorted({x[2] for x in res}):
        a = [x[3] for x in res if x[2] == w and x[4] == "traded"]
        b = [x[5] for x in res if x[2] == w and x[6] == "traded"]
        print(f"  W{w[1]}: معلّق {len(a):>3} {sum(a):+6.1f}R  ←  سوق {len(b):>3} {sum(b):+6.1f}R")
    if skipped:
        print(f"\n⚠️ بلا شموع: {', '.join(skipped)}")
    print("\n⚠️ استكشاف لا قرار: إن بدا السوق أفضل، يُسجَّل شرط قبول ثم يُقاس أسبوعين أماميين قبل أي تغيير بحساب النتائج.")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        start = datetime.strptime(arg, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        start = START
    asyncio.run(main(start))
