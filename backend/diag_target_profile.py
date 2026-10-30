"""
(2026-10-13) محاكاة للقراءة فقط: أي أسلوب إدارة للصفقة يقرّبنا من 60% ربح وأيام خاسرة أقل؟

هدف المالك: نسبة ربح ~60% وألا يكون يوم كامل خسائر — بمقياس أسبوعي لكل سوق. نفس الصفقات
ونفس الدخول والوقف كما صدرت فعلاً، تُعاد على شموع 5m الحقيقية بخمسة أساليب خروج:

  A) كما هو اليوم: TP1 ثم متابعة لـTP2 (TP1 يُقفل الربح إن ضُرب الوقف بعده)
  B) هدف 1R: إغلاق كامل عند ربح = المخاطرة
  C) نصف عند 1R + نقل الوقف للدخول + النصف الآخر حتى TP2
  D) هدف 0.7R: إغلاق كامل
  E) كما هو اليوم + نقل الوقف للدخول عند 1R (تنبيه التعادل الموجود)

قواعد الحلقة الحية (diag_gold.simulate): لا شيء قبل لمس الدخول؛ الوقف أولاً إن لُمس الاثنان بنفس
الشمعة؛ نقل الوقف يُفعَّل من الشمعة التالية (تحفّظ)؛ عند انتهاء المدة إغلاق بسعر آخر شمعة.
مصادر الشموع كقاعدة الحلقة: الذهب والفضة TradingView الفوري، غيرهما yfinance (60 يوماً حداً).
لا يكتب شيئاً.

    docker cp backend/diag_target_profile.py moshapi_backend:/app/
    docker exec moshapi_backend python diag_target_profile.py [أيام=14] [أساليب مثل CFLMO] 2>/dev/null
"""
import sys, asyncio
sys.path.insert(0, "/app")
from datetime import datetime, timedelta, timezone

import pandas as pd

from app.database import SessionLocal
from app.models.market_config import MarketConfig
from app.models.signal import Signal, SignalStatus
from app.services.decision_grouping import group_unique_decisions, merge_reissued

TRUSTED_FROM = datetime(2026, 9, 16, tzinfo=timezone.utc)
DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 14
SPOT_TV = {"XAUUSD", "XAGUSD"}
NAMES = {"crypto": "كريبتو", "forex": "فوركس", "commodity": "معادن وطاقة", "index": "مؤشرات"}
PROFILES = [("A", "كما هو اليوم"), ("B", "هدف 1R كامل"), ("C", "نصف عند 1R + تعادل + الباقي TP2"),
            ("D", "هدف 0.7R كامل"), ("E", "كما هو + تعادل عند 1R"),
            # (2026-10-14) TP1 أقرب (سقف 1R أو 1.5R) وTP2 كما هو — نفس محاسبة A تماماً (TP1 يُقفل النتيجة رابحة)
            ("H", "TP1 عند 0.7R + TP2 كما هو"), ("F", "TP1 عند 1R + TP2 كما هو"),
            ("G", "TP1 عند 1.5R + TP2 كما هو"),
            # (2026-10-14) محاسبة صادقة يقدر عليها المتداول فعلاً — A وF-H تعدّ TP1 ربحاً وتُبقي الصفقة كاملة لـTP2
            # معاً (مستحيل تنفيذياً). I/J = الأسلوب الحالي بصدق، C/K = TP1 قريب بصدق.
            ("I", "صادق: إغلاق كامل عند TP1 الحالي"), ("J", "صادق: نصف عند TP1 الحالي + تعادل + الباقي TP2"),
            ("K", "صادق: نصف عند 0.7R + تعادل + الباقي TP2"),
            # (2026-10-30) فكرة المالك: هدف ثانٍ عند 2.5R والبعيد يصير ثالثاً. L/M صادقان، وO بمحاسبة المنصة الحالية
            # (أعلى هدف بلغته الصفقة يُقفل كله) — مستحيل تنفيذياً، يُعرض فقط ليُرى أثر العدّ على الرقم المعلن مقابل F.
            ("L", "صادق: ثلث 1R + تعادل + ثلث 2.5R + ثلث البعيد"), ("M", "صادق: نصف 1R + تعادل + نصف 2.5R"),
            ("O", "محاسبة المنصة: 1R ثم 2.5R ثم البعيد")]
if len(sys.argv) > 2:                                            # (2026-10-30) لاختصار الناتج: مثلاً CFLMO
    PROFILES = [p for p in PROFILES if p[0] in sys.argv[2]]


async def _candles(sym):
    if sym in SPOT_TV:
        from app.services.tv_price_feed import TV_SYMBOL_MAP, fetch_tv_history
        bars = await fetch_tv_history(TV_SYMBOL_MAP[sym], "5m", bars=5000, timeout_s=40)
        if not bars:
            return None
        df = pd.DataFrame([(b[0], b[2], b[3], b[4]) for b in bars], columns=["ts", "high", "low", "close"])
        df["ts"] = pd.to_datetime(df.ts, unit="s", utc=True)
        return df.sort_values("ts").reset_index(drop=True)
    import yfinance as yf
    from app.services.smart_data import _resolve_yf_symbol
    m5 = yf.Ticker(_resolve_yf_symbol(sym)).history(period="60d", interval="5m", auto_adjust=True)
    if m5 is None or not len(m5):
        return None
    df = pd.DataFrame({"ts": pd.to_datetime(m5.index, utc=True), "high": m5.High.values,
                       "low": m5.Low.values, "close": m5.Close.values}).dropna()
    return df.sort_values("ts").reset_index(drop=True)


def _bars(rows, created, end_ts, entry):
    """الشموع من لحظة تفعّل الدخول حتى نهاية المدة. يعيد (قائمة، تفعّل؟)."""
    out, started = [], False
    for ts, hi, lo, cl in rows:
        if ts < created:
            continue
        if ts > end_ts:
            break
        if not started:
            if not (lo <= entry <= hi):
                continue
            started = True
        out.append((hi, lo, cl))
    return out, started


def run(rows, created, end_ts, entry, sl, tp1, tp2, is_buy, profile):
    """يعيد R للصفقة بالأسلوب المطلوب، أو None إن لم يتفعّل الدخول / ما زالت مفتوحة."""
    bars, started = _bars(rows, created, end_ts, entry)
    if not started:
        return None
    risk = abs(entry - sl)
    sgn = 1 if is_buy else -1
    lvl = lambda r: entry + sgn * r * risk
    r_of = lambda px: sgn * (px - entry) / risk
    reached = lambda hi, lo, px: (hi >= px) if is_buy else (lo <= px)
    sl_touch = lambda hi, lo, px: (lo <= px) if is_buy else (hi >= px)
    still_open = end_ts > datetime.now(timezone.utc)
    last_close = bars[-1][2]

    if profile in ("L", "M", "O"):
        far = r_of(tp2 if ((tp2 > tp1) if is_buy else (tp2 < tp1)) else tp1)
    if profile in ("L", "M"):
        # سلّم أهداف صادق: يُغلق جزء عند كل هدف، والوقف للدخول من الشمعة التالية لأول هدف. إن كان البعيد ≤ 2.5R فهدفان فقط.
        if far <= 1.0:
            steps = [(far, 1.0)]
        elif far <= 2.5:
            steps = [(1.0, 0.5), (far, 0.5)]
        elif profile == "M":
            steps = [(1.0, 0.5), (2.5, 0.5)]
        else:
            steps = [(1.0, 1 / 3), (2.5, 1 / 3), (far, 1 / 3)]
        cur_sl, armed, banked, left, i = sl, False, 0.0, 1.0, 0
        for hi, lo, _ in bars:
            if armed:
                cur_sl = entry
            if sl_touch(hi, lo, cur_sl):
                return banked + left * r_of(cur_sl)
            while i < len(steps) and reached(hi, lo, lvl(steps[i][0])):
                banked += steps[i][0] * steps[i][1]
                left -= steps[i][1]
                i += 1
                armed = True
            if i == len(steps):
                return banked
        return None if still_open else banked + left * r_of(last_close)

    if profile == "O":
        one = min(1.0, far)
        best = None
        for hi, lo, _ in bars:
            if sl_touch(hi, lo, sl):
                return -1.0 if best is None else best
            if reached(hi, lo, lvl(far)):
                return far
            if far > 2.5 and reached(hi, lo, lvl(2.5)):
                best = 2.5
            elif best is None and reached(hi, lo, lvl(one)):
                best = one
        if still_open:
            return None
        return r_of(last_close) if best is None else best

    if profile in ("C", "J", "K"):
        # النصف الأول يُغلق عند half_r (C: 1R، K: 0.7R، J: TP1 الأصلي)، ثم الوقف للدخول (من الشمعة
        # التالية)، والنصف الثاني حتى الهدف النهائي (TP2، أو TP1 إن لم يوجد TP2). إن كان الهدف النهائي
        # ≤ half_r يُغلق كاملاً عنده. هذا تنفيذ يقدر عليه المتداول فعلاً — محاسبة صادقة.
        half_r = {"C": 1.0, "K": 0.7}.get(profile) or r_of(tp1)
        final = tp2 if ((tp2 > tp1) if is_buy else (tp2 < tp1)) else tp1
        if r_of(final) <= half_r:
            for hi, lo, _ in bars:
                if sl_touch(hi, lo, sl):
                    return -1.0
                if reached(hi, lo, final):
                    return r_of(final)
            return None if still_open else r_of(last_close)
        cur_sl, half, armed = sl, False, False
        for hi, lo, _ in bars:
            if armed:
                cur_sl = entry
            if sl_touch(hi, lo, cur_sl):
                return (0.5 * half_r + 0.5 * r_of(cur_sl)) if half else -1.0
            if reached(hi, lo, final):
                return 0.5 * half_r + 0.5 * r_of(final)    # الوصول للنهائي يمر حتماً بمستوى النصف
            if reached(hi, lo, lvl(half_r)):
                half, armed = True, True
        if still_open:
            return None
        return (0.5 * half_r + 0.5 * r_of(last_close)) if half else r_of(last_close)

    if profile in ("B", "D", "I"):
        # إغلاق كامل عند هدف واحد: B عند 1R، D عند 0.7R، I عند TP1 الأصلي (محاسبة صادقة للأسلوب الحالي)
        target = tp1 if profile == "I" else lvl(1.0 if profile == "B" else 0.7)
        for hi, lo, _ in bars:
            if sl_touch(hi, lo, sl):
                return -1.0
            if reached(hi, lo, target):
                return r_of(target)
        return None if still_open else r_of(last_close)

    # A و E و F و G و H: TP1 يُقفل الربح، المتابعة حتى TP2؛ E ينقل الوقف للدخول بعد بلوغ 1R؛
    # F/G يقرّبان TP1 لـ1R/1.5R إن كان أبعد (وإلا يبقى كما هو) — TP2 لا يتغيّر
    if profile in ("F", "G", "H"):
        cap = {"F": 1.0, "G": 1.5, "H": 0.7}[profile]
        if r_of(tp1) > cap:
            tp1 = lvl(cap)
    has_t2 = (tp2 > tp1) if is_buy else (tp2 < tp1)
    cur_sl, armed, t1_hit = sl, False, False
    for hi, lo, _ in bars:
        if armed:
            cur_sl = entry
        if sl_touch(hi, lo, cur_sl):
            if t1_hit:
                return r_of(tp1)
            return 0.0 if cur_sl == entry else -1.0
        if profile == "E" and r_of(hi if is_buy else lo) >= 1.0:
            armed = True
        if has_t2 and reached(hi, lo, tp2):
            return r_of(tp2)
        if reached(hi, lo, tp1):
            t1_hit = True
            if not has_t2:
                return r_of(tp1)
    if still_open:
        return None
    return r_of(tp1) if t1_hit else r_of(last_close)


async def main():
    db = SessionLocal()
    since = max(TRUSTED_FROM, datetime.now(timezone.utc) - timedelta(days=DAYS))
    cat = {r[0].upper(): (r[1] or "?") for r in db.query(MarketConfig.symbol, MarketConfig.category).all()}
    rows = db.query(Signal).filter(
        Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT, SignalStatus.EXPIRED]),
        Signal.created_at >= since,
    ).all()
    db.close()
    by_id = {s.id: s for s in rows}
    decisions = merge_reissued(group_unique_decisions(rows))
    symbols = sorted({(d["market"] or "").upper() for d in decisions})
    print(f"📊 منذ {since:%Y-%m-%d}: {len(decisions)} قرار على {len(symbols)} رمز — المحاكاة جارية...\n")

    res = []      # (profile, category, week, day, r)
    skipped = []
    for sym in symbols:
        try:
            m5 = await _candles(sym)
        except Exception as e:
            skipped.append(f"{sym} ({type(e).__name__})")
            continue
        if m5 is None or not len(m5):
            skipped.append(f"{sym} (لا شموع)")
            continue
        data = list(zip(m5.ts, m5.high.astype(float), m5.low.astype(float), m5.close.astype(float)))
        for d in [x for x in decisions if (x["market"] or "").upper() == sym]:
            s = by_id[d["id"]]
            created = s.created_at if s.created_at.tzinfo else s.created_at.replace(tzinfo=timezone.utc)
            if created < m5.ts.iloc[0]:
                continue
            exp = s.expires_at or (created + timedelta(hours=24))
            exp = exp if exp.tzinfo else exp.replace(tzinfo=timezone.utc)
            entry, sl = float(s.entry_price), float(s.stop_loss)
            tp1 = float(s.take_profit_1)
            tp2 = float(s.take_profit_2 or tp1)
            if not abs(entry - sl):
                continue
            is_buy = (s.signal_type.value if hasattr(s.signal_type, "value") else s.signal_type) == "BUY"
            outs = {p: run(data, created, exp, entry, sl, tp1, tp2, is_buy, p) for p, _ in PROFILES}
            if any(v is None for v in outs.values()):
                continue                                         # نفس المجموعة بكل الأساليب
            for p, r in outs.items():
                res.append((p, cat.get(sym, "?"), created.isocalendar()[:2], created.date(), r))
        await asyncio.sleep(1.0)

    def block(items):
        n = len(items)
        if not n:
            return "—"
        w = sum(1 for x in items if x[4] > 0.001)
        z = sum(1 for x in items if abs(x[4]) <= 0.001)
        t = sum(x[4] for x in items)
        return f"{n:>4} | ربح {w / n * 100:4.0f}% | تعادل {z / n * 100:3.0f}% | {t:+7.1f}R ({t / n:+.2f})"

    def days(items):
        by = {}
        for x in items:
            by.setdefault(x[3], []).append(x[4])
        lose = sum(1 for v in by.values() if sum(v) < 0)
        all_lose = sum(1 for v in by.values() if len(v) >= 3 and all(r < -0.001 for r in v))
        return f"أيام خاسرة {lose}/{len(by)} | أيام كلها خسائر (3+ صفقات) {all_lose}"

    print("══ الإجمالي ══")
    for p, name in PROFILES:
        it = [x for x in res if x[0] == p]
        print(f"  {p}) {name:<32} {block(it)}   {days(it)}")

    cats = sorted({x[1] for x in res})
    for c in cats:
        print(f"\n══ {NAMES.get(c, c)} ══")
        for p, name in PROFILES:
            it = [x for x in res if x[0] == p and x[1] == c]
            print(f"  {p}) {name:<32} {block(it)}")

    print("\n══ أسبوعياً لكل سوق (R) ══")
    weeks = sorted({x[2] for x in res})
    for c in cats:
        print(f"  {NAMES.get(c, c)}:")
        for w in weeks:
            vals = []
            for p, _ in PROFILES:
                it = [x[4] for x in res if x[0] == p and x[1] == c and x[2] == w]
                vals.append(f"{p} {sum(it):+6.1f}R" if it else f"{p}    —  ")
            print(f"    W{w[1]}: " + "  ".join(vals))

    if skipped:
        print(f"\n⚠️ بلا شموع (لم تُحسب): {', '.join(skipped)}")
    print("⚠️ محاكاة على الماضي لا وعد بالمستقبل. الصفقات المفتوحة أو التي لم يتفعّل دخولها مستبعدة من كل الأساليب.")


if __name__ == "__main__":
    asyncio.run(main())
