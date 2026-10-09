"""
fix_pre_entry_outcomes.py — تصحيح نتائج سجّلتها حلقة الرصد من شمعة قبل الدخول
==========================================================================
الخلل (أُصلح بـbot.py 2026-10-09): بعد أن تُحفَظ entry_executed بدورة، كانت
الدورات التالية تمشي الشموع من created_at وتفحص ما قبل الدخول كأنه بعده.
فصفقة دخلت بعد أن عبر السعر الستوب (أو الهدف) قبل التفعيل كانت تُحسم بتلك
الشمعة. مثال مؤكَّد: #3234 ذهب بيع، سُجّل SL_HIT وسعر إغلاقه المسجّل 4192
رابح، والشموع تؤكد TP2. الخلل موجود منذ بوابة تفعيل الدخول (2026-09-24).

يُصحَّح الصف **فقط** إذا تحققت كل الشروط معاً (يقين، لا ترجيح):
  1) الشموع تغطي من الإنشاء حتى الحسم أو انتهاء المدة
  2) شمعة التفعيل في الشموع تطابق entry_executed المحفوظ (±10 دقائق)
     — أي أننا نرى نفس الصفقة التي رأتها الحلقة
  3) النتيجة المسجّلة لا تتكرر بعد الدخول (المشي الصحيح يعطي غيرها)
  4) المستوى المسجّل (الستوب أو الهدف) لُمس فعلاً بشمعة **قبل** الدخول
     — أي أن سبب الخطأ هو هذا الخلل تحديداً لا شيء آخر
أي صف لا يحقق الأربعة يُعرض "غير مؤكَّد" ولا يُلمس.

الاتجاهان يُصحَّحان: خسارة وهمية → ربح، وربح وهمي → خسارة. والحالة التي لم
تبلغ هدفاً ولا ستوباً فعلياً ضمن مدتها → EXPIRED (تخرج من الإحصاء).

المصادر نفسها التي تقرأها الحلقة: TradingView الفوري للذهب والفضة
(_SPOT_SYMBOLS بـbot.py)، وyfinance لبقية الرموز (60 يوماً من شموع 5m).
لا يلمس notes ولا يرسل أي إشعار.

⚠️ DRY-RUN افتراضياً. التطبيق بـ--apply صراحة.

التشغيل:
  docker cp backend/fix_pre_entry_outcomes.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/fix_pre_entry_outcomes.py 2>/dev/null
  docker exec moshapi_backend python /app/fix_pre_entry_outcomes.py --apply 2>/dev/null
"""
import sys, asyncio
sys.path.insert(0, "/app")

from collections import defaultdict, Counter
from datetime import datetime, timedelta, timezone
import pandas as pd

from app.database import SessionLocal
from app.models.signal import Signal, SignalStatus
from app.api.admin import _calc_points

BUG_SINCE = datetime(2026, 9, 24, tzinfo=timezone.utc)   # بوابة تفعيل الدخول
SPOT_TV = {"XAUUSD", "XAGUSD"}                            # = _SPOT_SYMBOLS بـbot.py
ALIGN_TOL = timedelta(minutes=10)
APPLY = "--apply" in sys.argv
# --exclude=US30,NAS100 — رموز تُستثنى من التطبيق (مرجع سعرها قيد التحقق)
EXCLUDE = {x.strip().upper() for a in sys.argv if a.startswith("--exclude=")
           for x in a.split("=", 1)[1].split(",") if x.strip()}
WIN = ("TP1_HIT", "TP2_HIT")


async def _tv_candles(sym):
    from app.services.tv_price_feed import TV_SYMBOL_MAP, fetch_tv_history
    bars = await fetch_tv_history(TV_SYMBOL_MAP[sym], "5m", bars=5000, timeout_s=40)
    if not bars:
        return None
    df = pd.DataFrame([(b[0], b[2], b[3]) for b in bars], columns=["ts", "high", "low"])
    df["ts"] = pd.to_datetime(df["ts"], unit="s", utc=True)
    return df


def _yf_candles(sym):
    import yfinance as yf
    from app.services.smart_data import _resolve_yf_symbol
    h = yf.Ticker(_resolve_yf_symbol(sym)).history(period="60d", interval="5m", auto_adjust=True)
    if h is None or not len(h):
        return None
    df = pd.DataFrame({"ts": pd.to_datetime(h.index, utc=True),
                       "high": h["High"].values, "low": h["Low"].values})
    return df.dropna()


def _aware(d):
    return d if (d is None or d.tzinfo) else d.replace(tzinfo=timezone.utc)


def walk(rows, created, end_ts, entry, sl, tp1, tp2, is_buy):
    """قواعد الحلقة الحية بعد الإصلاح: الشموع من created-60ث، لا شيء قبل
    لمس الدخول، الستوب أولاً، TP1 ليس نهائياً. يعيد (الحالة، وقت التفعيل،
    وقت الحسم، هل لُمس كل مستوى قبل الدخول)."""
    has_tp2 = (tp2 > tp1) if is_buy else (tp2 < tp1)
    start = created - timedelta(seconds=60)
    entry_ts = None
    status, exit_ts = None, None
    pre = {"SL": False, "TP1": False, "TP2": False}
    for ts, hi, lo in rows:
        if ts < start:
            continue
        if ts > end_ts:
            break
        sl_t = (lo <= sl) if is_buy else (hi >= sl)
        tp2_t = has_tp2 and ((hi >= tp2) if is_buy else (lo <= tp2))
        tp1_t = (hi >= tp1) if is_buy else (lo <= tp1)
        if entry_ts is None:
            if not (lo <= entry <= hi):
                pre["SL"] |= sl_t; pre["TP1"] |= tp1_t; pre["TP2"] |= tp2_t
                continue
            entry_ts = ts
        if sl_t:
            if status is None:
                status, exit_ts = "SL_HIT", ts
            break
        if tp2_t:
            status, exit_ts = "TP2_HIT", ts
            break
        if tp1_t and status is None:
            status, exit_ts = "TP1_HIT", ts
    return status, entry_ts, exit_ts, pre


async def main():
    db = SessionLocal()
    try:
        rows = (db.query(Signal)
                .filter(Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT]),
                        Signal.created_at >= BUG_SINCE,
                        Signal.entry_executed.isnot(None))
                .order_by(Signal.market, Signal.id).all())
        print(f"📊 صفوف محسومة منذ {BUG_SINCE.date()} بدخول مسجَّل: {len(rows)}  —  "
              f"{'تطبيق فعلي' if APPLY else 'معاينة فقط (DRY-RUN)'}\n")

        by_market = defaultdict(list)
        for s in rows:
            if s.market.upper() not in EXCLUDE:
                by_market[s.market.upper()].append(s)
        if EXCLUDE:
            print(f"⛔ مستثناة بالكامل: {', '.join(sorted(EXCLUDE))}\n")

        now = datetime.now(timezone.utc)
        changes, uncertain = [], []
        no_data = Counter()
        consistent = 0

        for mk, sigs in sorted(by_market.items()):
            try:
                df = await _tv_candles(mk) if mk in SPOT_TV else \
                     await asyncio.get_event_loop().run_in_executor(None, _yf_candles, mk)
            except Exception as e:
                df = None
                print(f"  ⚠️ {mk}: فشل جلب الشموع: {type(e).__name__}: {e}")
            if df is None or not len(df):
                no_data[mk] += len(sigs)
                continue
            df = df.sort_values("ts")
            data = list(zip(df.ts, df.high.astype(float), df.low.astype(float)))
            first_ts, last_ts = df.ts.iloc[0], df.ts.iloc[-1]
            await asyncio.sleep(1.0)

            for s in sigs:
                created = _aware(s.created_at)
                exp = _aware(s.expires_at) or (created + timedelta(hours=72))
                end = min(exp, now)
                if first_ts > created - timedelta(seconds=60):
                    no_data[mk] += 1
                    continue
                entry, sl = float(s.entry_price), float(s.stop_loss)
                tp1 = float(s.take_profit_1); tp2 = float(s.take_profit_2 or tp1)
                is_buy = (s.signal_type.value if hasattr(s.signal_type, "value") else s.signal_type) == "BUY"
                rec = s.status.value if hasattr(s.status, "value") else s.status

                st, ets, xts, pre = walk(data, created, end, entry, sl, tp1, tp2, is_buy)
                if st is None and last_ts < end:
                    no_data[mk] += 1          # الشموع لا تغطي المدة كاملة — لا حكم
                    continue
                if st is None and exp > now:
                    # لم تُحسم بالشموع ولسا ضمن مدتها — حكمها الصحيح "نشطة" لا
                    # EXPIRED؛ إرجاع صف مغلق لـACTIVE خارج نطاق هذا التصحيح
                    uncertain_open = True
                else:
                    uncertain_open = False
                truth = st or "EXPIRED"
                if truth == rec:
                    consistent += 1
                    continue

                ee = _aware(s.entry_executed)
                reasons = ["لم تُحسم بالشموع ولسا ضمن مدتها"] if uncertain_open else []
                if ets is None:
                    reasons.append("الشموع لا تُظهر تفعيلاً للدخول")
                elif abs(ets - ee) > ALIGN_TOL:
                    reasons.append(f"تفعيل الشموع {ets:%m-%d %H:%M} ≠ المسجّل {ee:%m-%d %H:%M}")
                lvl_key = "SL" if rec == "SL_HIT" else ("TP2" if rec == "TP2_HIT" else "TP1")
                if not pre[lvl_key]:
                    reasons.append(f"{lvl_key} لم يُلمس قبل الدخول — سبب الفرق ليس هذا الخلل")
                item = dict(s=s, mk=mk, rec=rec, truth=truth, ets=ets, xts=xts, ee=ee,
                            entry=entry, sl=sl, tp1=tp1, tp2=tp2, is_buy=is_buy, reasons=reasons)
                (uncertain if reasons else changes).append(item)

        # ── العرض ───────────────────────────────────────────────────────────
        kinds = Counter()
        print("✅ تصحيحات مؤكَّدة (الشروط الأربعة متحققة):")
        for it in changes:
            s = it["s"]
            kind = ("خسارة وهمية → ربح" if it["rec"] == "SL_HIT" and it["truth"] in WIN else
                    "ربح وهمي → خسارة" if it["rec"] in WIN and it["truth"] == "SL_HIT" else
                    "→ انتهت بلا نتيجة" if it["truth"] == "EXPIRED" else "تعديل مستوى الهدف")
            kinds[kind] += 1
            print(f"  #{s.id:5d} {it['mk']:10s} {s.timeframe:4s} {'BUY ' if it['is_buy'] else 'SELL'}  "
                  f"{it['rec']:8s} → {it['truth']:8s}  [{kind}]  "
                  f"تفعيل {it['ets']:%m-%d %H:%M}" + (f"  حسم {it['xts']:%m-%d %H:%M}" if it["xts"] else ""))

        if uncertain:
            print(f"\n⚠️ فروق غير مؤكَّدة — لن تُلمس ({len(uncertain)}):")
            for it in uncertain:
                print(f"  #{it['s'].id:5d} {it['mk']:10s} {it['rec']:8s} ≠ شموع {it['truth']:8s}  — "
                      + " · ".join(it["reasons"]))

        # ── التطبيق ─────────────────────────────────────────────────────────
        if APPLY:
            for it in changes:
                s, truth, entry = it["s"], it["truth"], it["entry"]
                if truth == "EXPIRED":
                    s.status = SignalStatus.EXPIRED
                    s.points_earned = None
                    s.profit_loss = 0.0
                    s.profit_loss_percentage = 0.0
                    s.current_price = None
                    s.exit_executed = None
                else:
                    exit_p = it["sl"] if truth == "SL_HIT" else it["tp2"] if truth == "TP2_HIT" else it["tp1"]
                    pts = _calc_points(s.market, abs(exit_p - entry), entry)
                    if truth == "SL_HIT":
                        pts = -pts
                    pct = ((exit_p - entry) if it["is_buy"] else (entry - exit_p)) / entry * 100
                    s.status = SignalStatus(truth)
                    s.points_earned = round(pts, 2)
                    s.profit_loss = round(pts, 2)
                    s.profit_loss_percentage = round(pct, 3)
                    s.current_price = exit_p
                    s.exit_executed = it["xts"].to_pydatetime() if hasattr(it["xts"], "to_pydatetime") else it["xts"]
                s.outcome_verified = True
            db.commit()

        print("\n" + "=" * 90)
        print(f"متطابقة مع الشموع: {consistent}   تصحيحات مؤكَّدة: {len(changes)}   "
              f"غير مؤكَّدة (لم تُلمس): {len(uncertain)}   بلا شموع كافية: {sum(no_data.values())}")
        for k, v in kinds.items():
            print(f"   {k}: {v}")
        if no_data:
            print(f"   بلا شموع كافية حسب الرمز: {dict(no_data)}")
        print("=" * 90)
        print("✅ تم التطبيق." if APPLY else "ℹ️ معاينة فقط — لم يُكتب شيء. للتطبيق: --apply")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
