"""
analyze_outcome_damage.py
============================
تحليل قراءة فقط — يقيس حجم الضرر الناتج عن عطلين مكتشفين اليوم
(16/09) بحلقة رصد النتائج، قبل أي تصحيح.

العطل الأول (أُصلح): المشي الزمني كان يرمي TypeError بسبب تجريد
المنطقة الزمنية (.values)، والاستثناء مبتلَع بـexcept Exception: pass —
فلم يعمل ولا مرة لأي رمز يمرّ من فرع yfinance، وسقط الرصد لفحص "أين
السعر الآن" فقط.

العطل الثاني (لم يُصلح بعد — يحتاج قراراً): السعر اللحظي المستخدم
بذلك الفحص يأتي من مصدر مختلف عن الشموع المستخدمة بالتحقق. للبيتكوين
مثلاً: Finnhub BINANCE:BTCUSDT للسعر، وyfinance BTC-USD للشموع —
أداتان مختلفتان يختلف سعرهما عادةً بعشرات الدولارات. فأي إشارة مسافة
وقفها أضيق من ذلك الفارق تكون نتيجتها محكومة بالمصدر لا بالسوق.
الحالة الشاهدة: #2521 وقفها 64.87 نقطة، سُجّلت SL_HIT بينما أعلى سعر
بالشموع بعد الإصدار كان أقل من الوقف بـ9 نقاط.

يقيس شيئين:
 1) فارق المصدرين الآن لكل رمز (أرضية الضجيج القياسية) — ويقارنها
    بمسافات الأوقاف الفعلية المستخدمة لذلك الرمز.
 2) كم إشارة مغلقة يختلف عليها حكم أداة التحقق عن المسجّل فعلاً.

لا يعدّل شيئاً. التصحيح قرار منفصل بعد رؤية الحجم.

التشغيل:
  docker cp analyze_outcome_damage.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/analyze_outcome_damage.py
"""
import sys, asyncio
sys.path.insert(0, "/app")

from datetime import datetime, timedelta, timezone
from collections import defaultdict

LOOKBACK_DAYS = 7
CLOSED = {"TP1_HIT", "TP2_HIT", "SL_HIT"}


async def main():
    from app.database import SessionLocal
    from app.models.signal import Signal, SignalStatus
    from app.services.smart_data import smart_data
    from app.api.admin import _verify_signal_outcome_core

    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
        rows = (db.query(Signal)
                  .filter(Signal.created_at >= cutoff)
                  .order_by(Signal.created_at.desc()).all())
        closed = [s for s in rows
                  if (s.status.value if hasattr(s.status, "value") else s.status) in CLOSED]

        # ── 1) أرضية الضجيج: فارق المصدرين الآن ──────────────────────────
        print("=" * 96)
        print("1) فارق مصدرَي السعر الآن مقابل مسافات الأوقاف المستخدمة فعلاً")
        print("=" * 96)
        print("  (السعر اللحظي = مسار get_realtime_price_with_meta، الشموع = get_ohlcv)")

        by_sym = defaultdict(list)
        for s in closed:
            try:
                e, sl = float(s.entry_price), float(s.stop_loss)
                if e > 0:
                    by_sym[s.market].append(abs(e - sl) / e * 100)
            except (TypeError, ValueError):
                pass

        for sym in sorted(by_sym, key=lambda k: -len(by_sym[k]))[:10]:
            sl_pcts = by_sym[sym]
            tightest = min(sl_pcts)
            try:
                meta = smart_data.get_realtime_price_with_meta(sym)
                live = float(meta["price"]) if meta else 0.0
                src  = meta.get("source", "?") if meta else "?"
            except Exception:
                live, src = 0.0, "فشل"
            try:
                df = await smart_data.get_ohlcv(sym, "5m", bars=3)
                candle = float(df["close"].iloc[-1]) if df is not None and len(df) else 0.0
            except Exception:
                candle = 0.0

            if live > 0 and candle > 0:
                gap_pct = abs(live - candle) / live * 100
                verdict = ("⛔ الفارق أكبر من أضيق وقف — نتائج غير قابلة للقياس"
                           if gap_pct >= tightest else "✅ الفارق دون أضيق وقف")
                print(f"\n  {sym:<10} لحظي={live:<12.2f}({src})  شمعة={candle:<12.2f}  "
                      f"الفارق={gap_pct:.4f}%")
                print(f"  {'':<10} أوقاف الرمز: أضيق={tightest:.4f}%  "
                      f"وسيط={sorted(sl_pcts)[len(sl_pcts)//2]:.4f}%  (ن={len(sl_pcts)})  → {verdict}")
            else:
                print(f"\n  {sym:<10} تعذّر جلب أحد المصدرين (لحظي={live}, شمعة={candle})")
            await asyncio.sleep(0.3)

        # ── 2) كم نتيجة مسجّلة يخالفها التحقق؟ ───────────────────────────
        print("\n" + "=" * 96)
        print(f"2) مراجعة النتائج المسجّلة آخر {LOOKBACK_DAYS} أيام بأداة التحقق السليمة")
        print("=" * 96)
        print(f"  إشارات مغلقة بالفترة: {len(closed)} — جاري الفحص...\n")

        agree = disagree = nodata = 0
        bad = []
        for i, s in enumerate(closed):
            if i and i % 20 == 0:
                print(f"    … {i}/{len(closed)}")
            try:
                r = await _verify_signal_outcome_core(s)
            except Exception as e:
                print(f"    #{s.id} فشل التحقق: {e}")
                continue
            det = r.get("detected")
            rec = s.status.value if hasattr(s.status, "value") else s.status
            if det in (None, "NO_DATA"):
                nodata += 1
            elif det == rec:
                agree += 1
            else:
                disagree += 1
                bad.append((s, rec, det, r.get("reason") or ""))
            await asyncio.sleep(0.25)

        print(f"\n  ✅ مطابق: {agree}    ⚠️ مخالف: {disagree}    "
              f"❓ لا بيانات: {nodata}")

        if bad:
            print("\n" + "-" * 96)
            print("الإشارات المخالفة (المسجّل ← الصحيح)")
            print("-" * 96)
            net = 0.0
            for s, rec, det, reason in bad:
                try:
                    e, sl = float(s.entry_price), float(s.stop_loss)
                    slp = abs(e - sl) / e * 100
                except (TypeError, ValueError):
                    slp = 0.0
                net += (s.points_earned or 0.0)
                print(f"  #{s.id:<5} {s.market:<9} {s.timeframe:<4} "
                      f"وقف={slp:6.3f}%  {rec:<9} ← {det:<13} "
                      f"نقاط مسجّلة={s.points_earned if s.points_earned is not None else 0:+8.2f}")
            print(f"\n  مجموع النقاط المسجّلة على الصفوف المخالفة: {net:+.2f}")
            print("  (أي أن هذا القدر من تقاريرنا مبني على نتائج لم يؤكدها السوق)")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
