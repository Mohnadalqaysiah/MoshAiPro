"""
diagnose_symbol_excursion.py
===============================
قراءة محضة — لا يعدّل صفاً ولا يمسّ المحرك.

السؤال الذي يحسمه: حين تخسر إشارات رمزٍ ما، هل **الاتجاه** خاطئ أم
**الهدف** بعيد عن متناول السوق؟ الفرق يقود لقرارين متعاكسين: الأول يعني
إيقاف الرمز، والثاني يعني تقريب هدفه — وإيقاف رمز اتجاهه سليم خسارةٌ
مضاعفة.

الدافع (16/09): الفضة أكبر خسارة مؤكدة بالمنصة — 38 قراراً، نسبة ربح
13.2%، توقّع −0.52R، صامدة في نصفَي الفترة. وبياناتها **الأقل تلوّثاً**
بيننا: أعطال حلقة الرصد أصابت الرموز التي تمرّ من yfinance، والفضة كانت
تُفحص بشموع TradingView فعمل مشيها الزمني طوال الوقت.

المنهج — MFE/MAE
-----------------
لكل إشارة، نمشي على شموع السوق الحقيقية من لحظة إصدارها ونقيس:
  • MFE = أقصى تحرّك **في صالحها** قبل أن تلمس وقفها (بمضاعف R).
  • MAE = أقصى تحرّك **ضدها**.

فإن كان MFE يبلغ 1R كثيراً بينما الهدف المُصدَر عند 3R أو 8R، فالاتجاه
كان سليماً والهدف خارج المتناول. وإن كان MFE يبقى قرب الصفر، فالاتجاه
نفسه خاطئ ولا يُصلحه تقريب الهدف.

ثم نحسب — من نفس القياس — نسبة الربح والتوقّع لكل هدف مُفترَض، فيظهر
**الهدف الأمثل تجريبياً لهذا الرمز** بدل تقديره.

⚠️ لا يُحتسب التحرّك المواتي داخل شمعة الوقف نفسها: ترتيبها الداخلي
مجهول، وافتراض بلوغ الهدف قبل الوقف داخلها يضخّم MFE بلا سند.

التشغيل:
  docker cp diagnose_symbol_excursion.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/diagnose_symbol_excursion.py XAGUSD 30
"""
import sys, asyncio
sys.path.insert(0, "/app")

from datetime import datetime, timedelta, timezone

TF_HOURS = {"1m": 2, "5m": 4, "15m": 8, "30m": 12, "1h": 24, "4h": 72, "1d": 168, "1w": 336}
TARGETS  = [0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0]


def excursion(candles, entry, sl, is_buy):
    """(MFE بمضاعف R، MAE بمضاعف R، هل لُمس الوقف) — التحرّك المواتي
    داخل شمعة الوقف لا يُحتسب (ترتيبها الداخلي مجهول)."""
    risk = abs(entry - sl)
    if risk <= 0:
        return None, None, None
    mfe = mae = 0.0
    for _ts, hi, lo in candles:
        sl_hit = (lo <= sl) if is_buy else (hi >= sl)
        if sl_hit:
            return round(mfe / risk, 3), round(max(mae, risk) / risk, 3), True
        fav = (hi - entry) if is_buy else (entry - lo)
        adv = (entry - lo) if is_buy else (hi - entry)
        mfe = max(mfe, fav)
        mae = max(mae, adv)
    return round(mfe / risk, 3), round(mae / risk, 3), False


async def main():
    symbol = (sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].isdigit() else "XAGUSD").upper()
    days   = next((int(a) for a in sys.argv[1:] if a.isdigit()), 30)

    from app.database import SessionLocal
    from app.models.signal import Signal
    from app.services.decision_grouping import group_unique_decisions
    from app.services.smart_data import smart_data as _sd
    import pandas as pd

    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        raw = (db.query(Signal)
                 .filter(Signal.created_at >= cutoff,
                         Signal.market.ilike(symbol))
                 .all())
        decisions = group_unique_decisions(raw)
        meta = {s.id: s for s in raw}

        print("=" * 96)
        print(f"تشريح تحرّك السوق — {symbol} · آخر {days} يوماً")
        print("=" * 96)
        print(f"  قرارات فريدة: {len(decisions)}")
        print("  السؤال: الاتجاه خاطئ، أم الهدف بعيد عن متناول السوق؟\n")
        if not decisions:
            print("  لا قرارات بهذه الفترة.")
            return

        df = await _sd.get_ohlcv(symbol, "5m", bars=5000)
        if df is None or not len(df):
            print("  تعذّر جلب الشموع.")
            return
        tcol = df["datetime"] if "datetime" in df.columns else df.index
        ts = pd.to_datetime(tcol, utc=True)
        rows = sorted(((t.timestamp(), float(h), float(l))
                       for t, h, l in zip(ts, df["high"], df["low"])), key=lambda r: r[0])
        span = (rows[-1][0] - rows[0][0]) / 86400
        print(f"  شموع متاحة: {len(rows)} — تغطي {span:.1f} يوماً\n")

        print("-" * 96)
        print(f"  {'#':<6}{'نوع':<6}{'فريم':<6}{'وقف%':>7}{'هدف مُصدَر':>11}"
              f"{'MFE':>8}{'MAE':>8}  الحكم")
        print("-" * 96)

        recs, skipped = [], 0
        for d in sorted(decisions, key=lambda x: x["created_at"]):
            s = meta.get(d["id"])
            if s is None:
                continue
            created = s.created_at
            if created and created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if not created:
                skipped += 1
                continue
            c_ts = created.timestamp()
            if rows[0][0] > c_ts:
                skipped += 1
                continue
            window = [r for r in rows if c_ts <= r[0] <= c_ts + TF_HOURS.get(s.timeframe, 24) * 3600]
            if not window:
                skipped += 1
                continue

            try:
                entry = float(s.entry_price); sl = float(s.stop_loss)
                tp1 = float(s.take_profit_1)
            except (TypeError, ValueError):
                skipped += 1
                continue
            is_buy = (s.signal_type.value if hasattr(s.signal_type, "value")
                      else s.signal_type) == "BUY"
            risk = abs(entry - sl)
            if risk <= 0 or entry <= 0:
                skipped += 1
                continue

            mfe, mae, hit_sl = excursion(window, entry, sl, is_buy)
            if mfe is None:
                skipped += 1
                continue

            tp1_r  = abs(tp1 - entry) / risk
            sl_pct = risk / entry * 100

            if mfe >= tp1_r:
                verdict = "بلغ الهدف المُصدَر"
            elif mfe >= 1.0:
                verdict = f"⚠ بلغ {mfe:.1f}R — الاتجاه سليم والهدف بعيد"
            elif mfe >= 0.5:
                verdict = f"تحرّك {mfe:.1f}R فقط"
            else:
                verdict = "✗ لم يتحرّك لصالحها — الاتجاه خاطئ"

            print(f"  {s.id:<6}{'شراء' if is_buy else 'بيع':<6}{s.timeframe:<6}"
                  f"{sl_pct:>6.3f}%{tp1_r:>10.2f}R{mfe:>7.2f}R{mae:>7.2f}R  {verdict}")
            recs.append({"mfe": mfe, "tp1_r": tp1_r, "sl_pct": sl_pct, "is_buy": is_buy})

        n = len(recs)
        print("-" * 96)
        print(f"  حُلّلت {n} من {len(decisions)}   (سقطت لنقص شموع: {skipped})")
        if n < 8:
            print("\n  ⚠️ العينة أصغر من أن يُبنى عليها. وسّع الفترة أو انتظر تراكماً.")
            return

        # ── التشخيص الأساسي ──────────────────────────────────────────
        wrong_dir = sum(1 for r in recs if r["mfe"] < 0.5)
        right_far = sum(1 for r in recs if r["mfe"] >= 1.0 and r["mfe"] < r["tp1_r"])
        reached   = sum(1 for r in recs if r["mfe"] >= r["tp1_r"])

        print("\n" + "=" * 96)
        print("التشخيص")
        print("=" * 96)
        print(f"  بلغت هدفها المُصدَر            : {reached:>3}  ({reached/n*100:.0f}%)")
        print(f"  الاتجاه سليم والهدف بعيد      : {right_far:>3}  ({right_far/n*100:.0f}%)"
              f"   ← يُصلحه تقريب الهدف")
        print(f"  لم تتحرّك لصالحها إطلاقاً       : {wrong_dir:>3}  ({wrong_dir/n*100:.0f}%)"
              f"   ← لا يُصلحه الهدف")

        med_tp1 = sorted(r["tp1_r"] for r in recs)[n // 2]
        med_mfe = sorted(r["mfe"] for r in recs)[n // 2]
        print(f"\n  الهدف المُصدَر (وسيط)  : {med_tp1:.2f}R")
        print(f"  ما بلغه السوق (وسيط) : {med_mfe:.2f}R")
        if med_tp1 > med_mfe * 1.5:
            print("  ⇒ الهدف المُصدَر أبعد بكثير مما يبلغه السوق عادةً لهذا الرمز.")

        # ── الهدف الأمثل تجريبياً ────────────────────────────────────
        print("\n" + "=" * 96)
        print("الهدف الأمثل تجريبياً — من نفس القياس")
        print("=" * 96)
        print(f"  {'الهدف':<8}{'نسبة الربح':>12}{'التوقّع':>11}   (الخسارة = −1R دائماً)")
        print("  " + "-" * 48)
        best = None
        for t in TARGETS:
            wins = sum(1 for r in recs if r["mfe"] >= t)
            wr   = wins / n
            exp  = wr * t - (1 - wr)
            flag = ""
            if best is None or exp > best[1]:
                best = (t, exp, wr)
            print(f"  {t:<8.2f}{wr*100:>11.1f}%{exp:>+11.2f}{flag}")
        print("  " + "-" * 48)
        if best:
            t, exp, wr = best
            print(f"  ⇒ الأعلى توقّعاً: هدف عند {t:.2f}R "
                  f"— نسبة ربح {wr*100:.0f}% وتوقّع {exp:+.2f}R")
        print("\n  ⚠️ حساب تقريبي: يفترض الخروج الكامل عند الهدف، ويهمل الهدف")
        print("     الثاني والسبريد والانزلاق. يُقرأ كترتيب مفاضلة لا كوعد.")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
