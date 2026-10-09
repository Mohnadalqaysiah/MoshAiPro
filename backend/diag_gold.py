"""
diag_gold.py — تشخيص قراءة فقط: لماذا تخسر صفقات الذهب؟ (2026-10-09)
======================================================================
تقرير الجودة (7 أيام): XAUUSD 17 قراراً، 1 رابحة / 16 خاسرة، −0.80R، ثابتة
بالنصفين. لكل سبب محتمل إصلاح مختلف، فنقيس قبل أن نعدّل:

  1) الستوب داخل تذبذب الذهب؟  → كم دقيقة صمدت، ومسافة الستوب ÷ ATR الساعة
  2) الاتجاه صحيح والإدارة خاطئة؟ → أقصى ربح بلغته (MFE بالـR) قبل الستوب
  3) عكس الاتجاه الكبير؟         → اتجاه 4h (EMA50) لحظة الإشارة

ثم يحاكي على نفس الصفقات ونفس الشموع (لا يعدّل شيئاً):
  - الأساس: المستويات الأصلية بنفس قواعد حلقة الرصد
  - ستوب أوسع = max(الأصلي، k × ATR الساعة)، k = 1.0 و 1.5
      (أ) الأهداف بنفس أسعارها  (ب) الأهداف تبتعد بنفس مضاعف R
  - فلتر الاتجاه: حذف الصفقات عكس اتجاه 4h

الشموع: TradingView الفورية (نفس مرجع مستويات المعادن ونفس حلقة الرصد)،
لا العقود الآجلة — راجع _verify_signal_outcome_core بـadmin.py.

التشغيل:
  docker cp backend/diag_gold.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/diag_gold.py 2>/dev/null              # ذهب، 14 يوم
  docker exec moshapi_backend python /app/diag_gold.py XAGUSD 14 2>/dev/null    # أي معدن/رمز بـTV
"""
import sys, asyncio
sys.path.insert(0, "/app")

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import pandas as pd

from app.database import SessionLocal
from app.models.signal import Signal, SignalStatus
from app.services.decision_grouping import group_unique_decisions
from app.services.tv_price_feed import TV_SYMBOL_MAP, fetch_tv_history

TRUSTED_FROM = datetime(2026, 9, 16, tzinfo=timezone.utc)   # قبلها حلقة رصد معطوبة
SYMBOL = (sys.argv[1] if len(sys.argv) > 1 else "XAUUSD").upper()
DAYS = int(sys.argv[2]) if len(sys.argv) > 2 else 14


def _df(bars):
    df = pd.DataFrame([(b[0], b[1], b[2], b[3], b[4]) for b in bars],
                      columns=["ts", "open", "high", "low", "close"])
    df["ts"] = pd.to_datetime(df["ts"], unit="s", utc=True)
    return df.sort_values("ts").reset_index(drop=True)


async def _fetch(tv_sym):
    m5 = await fetch_tv_history(tv_sym, "5m", bars=5000, timeout_s=40)
    await asyncio.sleep(1)
    h1 = await fetch_tv_history(tv_sym, "1h", bars=800, timeout_s=30)
    await asyncio.sleep(1)
    h4 = await fetch_tv_history(tv_sym, "4h", bars=400, timeout_s=30)
    return m5, h1, h4


def simulate(rows, created, end_ts, entry, sl, tp1, tp2, is_buy):
    """نفس قواعد bot_check_outcomes: لا شيء قبل لمس الدخول، الستوب أولاً عند
    الالتباس، TP1 ليس نهائياً، وعند انتهاء المدة: TP1 إن لُمس وإلا إغلاق
    بسعر آخر شمعة. يعيد (الحالة، R، وقت الدخول، وقت الخروج، MFE بالـR)."""
    risk = abs(entry - sl)
    has_tp2 = (tp2 > tp1) if is_buy else (tp2 < tp1)
    entry_ts = tp1_ts = None
    mfe = 0.0
    last_close = None
    last_ts = None
    for ts, hi, lo, cl in rows:
        if ts < created:
            continue
        if ts > end_ts:
            break
        if entry_ts is None:
            if not (lo <= entry <= hi):
                continue
            entry_ts = ts
        fav = (hi - entry) if is_buy else (entry - lo)
        mfe = max(mfe, fav / risk)
        last_close, last_ts = cl, ts
        sl_hit = (lo <= sl) if is_buy else (hi >= sl)
        tp2_hit = has_tp2 and ((hi >= tp2) if is_buy else (lo <= tp2))
        tp1_hit = (hi >= tp1) if is_buy else (lo <= tp1)
        if sl_hit:
            if tp1_ts:
                return "TP1_HIT", abs(tp1 - entry) / risk, entry_ts, tp1_ts, mfe
            return "SL_HIT", -1.0, entry_ts, ts, mfe
        if tp2_hit:
            return "TP2_HIT", abs(tp2 - entry) / risk, entry_ts, ts, mfe
        if tp1_hit and tp1_ts is None:
            tp1_ts = ts
    if entry_ts is None:
        return "NOT_TRIGGERED", None, None, None, 0.0
    if tp1_ts:
        return "TP1_HIT", abs(tp1 - entry) / risk, entry_ts, tp1_ts, mfe
    if end_ts > datetime.now(timezone.utc):
        return "OPEN", None, entry_ts, None, mfe
    move = (last_close - entry) if is_buy else (entry - last_close)
    return "EXPIRY_CLOSE", move / risk, entry_ts, last_ts, mfe


def summarize(label, results):
    rs = [r for r in results if r is not None]
    if not rs:
        print(f"  {label:44s} لا صفقات محسومة")
        return
    w = sum(1 for r in rs if r > 0)
    print(f"  {label:44s} صفقات={len(rs):3d}  رابحة={w:3d}  خاسرة={len(rs)-w:3d}  "
          f"نجاح={w*100/len(rs):5.1f}%  متوسط={sum(rs)/len(rs):+.2f}R  مجموع={sum(rs):+.1f}R")


def bucket(v, edges, labels):
    for e, l in zip(edges, labels):
        if v < e:
            return l
    return labels[-1]


def main():
    tv_sym = TV_SYMBOL_MAP.get(SYMBOL)
    if not tv_sym:
        print(f"⚠️ {SYMBOL} ليس له رمز TradingView بـTV_SYMBOL_MAP — هذا التشخيص يعمل على شموع TV فقط")
        return

    db = SessionLocal()
    since = max(TRUSTED_FROM, datetime.now(timezone.utc) - timedelta(days=DAYS))
    statuses = [SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT, SignalStatus.EXPIRED]
    sigs = db.query(Signal).filter(Signal.market == SYMBOL, Signal.status.in_(statuses),
                                   Signal.created_at >= since).all()
    db.close()
    by_id = {s.id: s for s in sigs}
    groups = group_unique_decisions(sigs)
    print(f"📊 {SYMBOL} منذ {since:%Y-%m-%d}: {len(sigs)} صف = {len(groups)} قرار فريد\n")
    if not groups:
        return

    m5b, h1b, h4b = asyncio.run(_fetch(tv_sym))
    if not m5b or not h1b or not h4b:
        print("⚠️ تعذّر جلب شموع TV (ربما تقييد مؤقت 429) — أعد التشغيل بعد دقيقة")
        return
    m5, h1, h4 = _df(m5b), _df(h1b), _df(h4b)
    print(f"شموع 5m من {m5.ts.iloc[0]:%m-%d %H:%M} إلى {m5.ts.iloc[-1]:%m-%d %H:%M} UTC ({len(m5)} شمعة)\n")

    tr = pd.concat([h1.high - h1.low, (h1.high - h1.close.shift()).abs(),
                    (h1.low - h1.close.shift()).abs()], axis=1).max(axis=1)
    h1["atr"] = tr.rolling(14).mean()
    h4["ema50"] = h4.close.ewm(span=50, adjust=False).mean()
    rows = list(zip(m5.ts, m5.high.astype(float), m5.low.astype(float), m5.close.astype(float)))

    recs = []
    skipped_old = 0
    for g in sorted(groups, key=lambda g: by_id[g["id"]].created_at):
        s = by_id[g["id"]]
        created = s.created_at if s.created_at.tzinfo else s.created_at.replace(tzinfo=timezone.utc)
        if created < m5.ts.iloc[0]:
            skipped_old += 1
            continue
        exp = s.expires_at or (created + timedelta(hours=24))
        exp = exp if exp.tzinfo else exp.replace(tzinfo=timezone.utc)
        entry, sl = float(s.entry_price), float(s.stop_loss)
        tp1 = float(s.take_profit_1); tp2 = float(s.take_profit_2 or tp1)
        is_buy = (s.signal_type.value if hasattr(s.signal_type, "value") else s.signal_type) == "BUY"
        risk = abs(entry - sl)
        if not risk:
            continue

        a = h1[h1.ts < created].tail(1)
        atr = float(a.atr.iloc[0]) if len(a) and pd.notna(a.atr.iloc[0]) else None
        e4 = h4[h4.ts < created].tail(6)
        trend = "?"
        if len(e4) == 6 and pd.notna(e4.ema50.iloc[-1]):
            px, ema, slope = float(e4.close.iloc[-1]), float(e4.ema50.iloc[-1]), float(e4.ema50.iloc[-1] - e4.ema50.iloc[0])
            trend = "UP" if (px > ema and slope > 0) else "DOWN" if (px < ema and slope < 0) else "FLAT"
        align = "مع" if (trend == "UP" and is_buy) or (trend == "DOWN" and not is_buy) \
            else "عكس" if trend in ("UP", "DOWN") else "محايد"

        st, r, ets, xts, mfe = simulate(rows, created, exp, entry, sl, tp1, tp2, is_buy)
        mins = round((xts - ets).total_seconds() / 60) if ets and xts else None
        recorded = s.status.value if hasattr(s.status, "value") else s.status

        sims = {}
        for k in (1.0, 1.5):
            if not atr:
                sims[k] = (None, None); continue
            new_risk = max(risk, k * atr)
            sl2 = entry - new_risk if is_buy else entry + new_risk
            d = 1 if is_buy else -1
            # (أ) الأهداف بنفس أسعارها
            ra = simulate(rows, created, exp, entry, sl2, tp1, tp2, is_buy)[1]
            # (ب) الأهداف بنفس مضاعف R
            m1, m2 = abs(tp1 - entry) / risk, abs(tp2 - entry) / risk
            rb = simulate(rows, created, exp, entry, sl2, entry + d * m1 * new_risk,
                          entry + d * m2 * new_risk, is_buy)[1]
            sims[k] = (ra, rb)

        recs.append(dict(id=s.id, tf=s.timeframe, side="BUY" if is_buy else "SELL", created=created,
                         recorded=recorded, sim=st, r=r, mins=mins, mfe=mfe,
                         sl_pct=risk / entry * 100, sl_atr=(risk / atr) if atr else None,
                         trend=trend, align=align, conf=s.ai_confidence, sims=sims))

    if skipped_old:
        print(f"ℹ️ {skipped_old} قرار أقدم من بداية شموع 5m المتاحة — خارج التشخيص\n")

    print(f"{'#':>6s} {'فريم':4s} {'اتجاه':5s} {'التاريخ':11s} {'مسجّل':8s} {'محاكاة':12s} {'R':>6s} "
          f"{'دقائق':>6s} {'MFE':>5s} {'ستوب%':>6s} {'ستوب/ATR':>8s} {'4h':4s} {'مع/عكس':6s} {'ثقة':>4s}")
    def _f(v, fmt):
        return format(v, fmt) if v is not None else "—"

    for x in recs:
        print(f"{x['id']:>6d} {x['tf']:4s} {x['side']:5s} {x['created']:%m-%d %H:%M} {x['recorded']:8s} "
              f"{x['sim']:12s} {_f(x['r'], '+.2f'):>6s} {_f(x['mins'], 'd'):>6s} {x['mfe']:>5.2f} "
              f"{x['sl_pct']:>5.2f}% {_f(x['sl_atr'], '.2f'):>8s} "
              f"{x['trend']:4s} {x['align']:6s} {x['conf'] or 0:>4.0f}")

    decided = [x for x in recs if x["r"] is not None]
    losses = [x for x in decided if x["sim"] == "SL_HIT"]

    print("\n" + "=" * 100)
    print("1) الخسائر — كم صمدت وكم بلغت لصالحها قبل الستوب")
    if losses:
        tb = defaultdict(int); mb = defaultdict(int)
        for x in losses:
            tb[bucket(x["mins"] or 0, [15, 60, 240], ["< 15د", "15-60د", "1-4س", "> 4س"])] += 1
            mb[bucket(x["mfe"], [0.3, 1.0], ["< 0.3R (لم تتحرك لصالحها)", "0.3-1R", "≥ 1R (ربحت ثم انعكست)"])] += 1
        print("   مدة الصمود:  " + "   ".join(f"{k}: {v}" for k, v in tb.items()))
        print("   أقصى ربح قبل الستوب:  " + "   ".join(f"{k}: {v}" for k, v in mb.items()))

    print("\n2) مسافة الستوب ÷ ATR الساعة (كل الصفقات المحسومة)")
    ab = defaultdict(list)
    for x in decided:
        if x["sl_atr"] is not None:
            ab[bucket(x["sl_atr"], [0.5, 1.0, 2.0], ["< 0.5", "0.5-1", "1-2", "≥ 2"])].append(x["r"])
    for k in ["< 0.5", "0.5-1", "1-2", "≥ 2"]:
        summarize(f"ستوب/ATR {k}", ab.get(k, []))

    print("\n3) مع اتجاه 4h أم عكسه")
    for k in ["مع", "عكس", "محايد"]:
        summarize(f"{k} الاتجاه", [x["r"] for x in decided if x["align"] == k])
    for k in ["BUY", "SELL"]:
        summarize(f"اتجاه الصفقة {k}", [x["r"] for x in decided if x["side"] == k])
    for tf in sorted({x["tf"] for x in decided}):
        summarize(f"فريم {tf}", [x["r"] for x in decided if x["tf"] == tf])

    print("\n4) محاكاة على نفس الصفقات ونفس الشموع")
    summarize("الأساس (المستويات الأصلية)", [x["r"] for x in decided])
    # نفس مجموعة الصفقات المحسومة بالأساس — مقارنة عادلة
    for k in (1.0, 1.5):
        summarize(f"ستوب ≥ {k}×ATR — أهداف بنفس السعر", [x["sims"][k][0] for x in decided])
        summarize(f"ستوب ≥ {k}×ATR — أهداف بنفس R", [x["sims"][k][1] for x in decided])
    summarize("فلتر: حذف الصفقات عكس اتجاه 4h", [x["r"] for x in decided if x["align"] != "عكس"])
    n_all = len(decided); n_kept = sum(1 for x in decided if x["align"] != "عكس")
    print(f"   (الفلتر يُبقي {n_kept} من {n_all} صفقة)")

    rec_wins = sum(1 for x in recs if x["recorded"] in ("TP1_HIT", "TP2_HIT"))
    rec_loss = sum(1 for x in recs if x["recorded"] == "SL_HIT")
    sim_wins = sum(1 for x in recs if x["sim"] in ("TP1_HIT", "TP2_HIT"))
    sim_loss = sum(1 for x in recs if x["sim"] == "SL_HIT")
    print(f"\nتطابق المحاكاة مع المسجّل: مسجّل {rec_wins}ر/{rec_loss}خ — محاكاة {sim_wins}ر/{sim_loss}خ"
          f"  (فرق كبير ⇒ لا يُعتمد على المحاكاة)")
    print("=" * 100)
    print("⚠️ عينة صغيرة: أي نسبة هنا مؤشر لا حكم. المحاكاة على الماضي لا وعد بالمستقبل.")


if __name__ == "__main__":
    main()
