"""
diagnose_metals_reference.py
===============================
الخطوة 1 — تشخيص قراءة محضة، لا يعدّل أي صف ولا يمسّ محرك التوليد.

السؤال الذي يحسمه: خلاف صفوف الفضة/الذهب — هل هو خطأ رصد حقيقي، أم
أن المستويات والتحقق يقيسان بمرجعين مختلفين؟

لماذا السؤال قائم أصلاً: مستويات المعادن تُبنى على شموع آجلة
(SI=F/GC=F) ثم يزيحها _apply_spot_basis للفوري بطرح basis مصدره أحد
ثلاثة — TV الفوري، أو TwelveData، أو معادلة carry نظرية — أيّها توفّر
لحظتها. ولا نسجّل أيّها استُخدم. بينما التحقق يقارن دائماً بشموع TV
الفورية. فإن كانت المستويات مبنية على carry نظري، فالمقارنة باطلة
بنيوياً مهما كانت أداة التحقق سليمة.

المنهج: لكل إشارة، عند لحظة إنشائها بالضبط، نقارن سعر دخولها بـ:
  • شمعة OANDA:XAGUSD / OANDA:XAUUSD  (الفوري الحقيقي — مرجع التحقق)
  • شمعة SI=F / GC=F                   (الآجل — مرجع بناء البنية)
الأقرب منهما يكشف المرجع الفعلي للمستويات.

⚠️ سعر الدخول مستوى مشتق من البنية لا سعر السوق اللحظي، فلا يُتوقع
تطابق تام — المعوَّل عليه هو أيّ المرجعين أقرب بفارق واضح، لا التطابق.

التشغيل:
  docker cp diagnose_metals_reference.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/diagnose_metals_reference.py
"""
import sys, asyncio
sys.path.insert(0, "/app")

from datetime import datetime, timedelta, timezone

# الصفوف المتنازع عليها من مخرجات fix_outcome_discrepancies (16/09)
DISPUTED = [2483, 2470, 2469, 2468, 2446, 2445, 2444,
            2443, 2442, 2441, 2358, 2356, 2355, 2507]

TV_MAP  = {"XAUUSD": "OANDA:XAUUSD", "XAGUSD": "OANDA:XAGUSD"}
FUT_MAP = {"XAUUSD": "GC=F",         "XAGUSD": "SI=F"}


def bar_at(rows, target):
    """أقرب شمعة زمنياً للحظة المطلوبة، أو None إن كانت البيانات لا تصلها."""
    best, best_gap = None, None
    for ts, hi, lo, close in rows:
        gap = abs((ts - target).total_seconds())
        if best_gap is None or gap < best_gap:
            best, best_gap = (ts, hi, lo, close), gap
    if best is None or best_gap is None or best_gap > 3600:
        return None
    return best


async def main():
    from app.database import SessionLocal
    from app.models.signal import Signal
    from app.services.smart_data import smart_data
    from app.services.tv_price_feed import fetch_tv_history
    import pandas as pd

    db = SessionLocal()
    try:
        sigs = db.query(Signal).filter(Signal.id.in_(DISPUTED)).all()
        sigs.sort(key=lambda s: s.created_at)
        if not sigs:
            print("لا توجد صفوف بالأرقام المطلوبة.")
            return

        # كاش لكل رمز — لا نكرر الجلب
        tv_cache, fut_cache = {}, {}

        print("=" * 100)
        print("تشخيص مرجع أسعار المعادن — قراءة فقط")
        print("=" * 100)
        print("  السؤال: سعر الدخول أقرب لأي مرجع؟ الفوري (مرجع التحقق) أم الآجل؟\n")

        verdicts = {"فوري": 0, "آجل": 0, "غير حاسم": 0, "لا بيانات": 0}

        for s in sigs:
            sym = s.market.upper()
            created = s.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            entry = float(s.entry_price or 0)
            status = s.status.value if hasattr(s.status, "value") else s.status

            # ── شموع TV الفورية ──────────────────────────────────────────
            if sym not in tv_cache:
                rows = []
                try:
                    bars = await fetch_tv_history(TV_MAP[sym], "5m", bars=3000)
                    for b in (bars or []):
                        rows.append((datetime.fromtimestamp(float(b[0]), tz=timezone.utc),
                                     float(b[2]), float(b[3]), float(b[4])))
                except Exception as e:
                    print(f"  ⚠️ تعذّر جلب شموع TV لـ{sym}: {e}")
                tv_cache[sym] = rows

            # ── شموع الآجل ───────────────────────────────────────────────
            if sym not in fut_cache:
                rows = []
                try:
                    df = await smart_data.get_ohlcv(sym, "5m", bars=3000)
                    if df is not None and len(df):
                        tcol = df["datetime"] if "datetime" in df.columns else df.index
                        ts = pd.to_datetime(tcol, utc=True)
                        for t, hi, lo, cl in zip(ts, df["high"], df["low"], df["close"]):
                            rows.append((t.to_pydatetime(), float(hi), float(lo), float(cl)))
                except Exception as e:
                    print(f"  ⚠️ تعذّر جلب شموع الآجل لـ{sym}: {e}")
                fut_cache[sym] = rows

            tv  = bar_at(tv_cache[sym],  created)
            fut = bar_at(fut_cache[sym], created)

            print("-" * 100)
            print(f"#{s.id}  {sym}  {s.timeframe}  {status}  أُنشئت {created:%m-%d %H:%M} UTC")
            print(f"   سعر الدخول: {entry}")

            if not tv and not fut:
                print("   ❓ البيانات المتاحة لا تصل لهذا التاريخ بأي مرجع.")
                verdicts["لا بيانات"] += 1
                continue

            d_tv = d_fut = None
            if tv:
                mid_tv = (tv[1] + tv[2]) / 2
                d_tv = abs(entry - mid_tv)
                print(f"   الفوري  (TV):  {tv[2]:.5f} – {tv[1]:.5f}   "
                      f"وسط={mid_tv:.5f}   فارق عن الدخول={d_tv:.5f}")
            else:
                print("   الفوري  (TV):  لا بيانات لهذه اللحظة")
            if fut:
                mid_fut = (fut[1] + fut[2]) / 2
                d_fut = abs(entry - mid_fut)
                print(f"   الآجل        :  {fut[2]:.5f} – {fut[1]:.5f}   "
                      f"وسط={mid_fut:.5f}   فارق عن الدخول={d_fut:.5f}")
            else:
                print("   الآجل        :  لا بيانات لهذه اللحظة")

            if tv and fut:
                basis = ((fut[1] + fut[2]) / 2) - ((tv[1] + tv[2]) / 2)
                print(f"   الـbasis الفعلي وقتها (آجل − فوري) = {basis:+.5f}")

            if d_tv is not None and d_fut is not None:
                ratio = (d_fut / d_tv) if d_tv > 0 else float("inf")
                if d_tv < d_fut and ratio >= 2:
                    print("   ⇒ المستويات مبنية على الفوري ✅ — مرجع التحقق مطابق، الخلاف حقيقي")
                    verdicts["فوري"] += 1
                elif d_fut < d_tv and (d_tv / d_fut if d_fut > 0 else float("inf")) >= 2:
                    print("   ⇒ المستويات مبنية على الآجل ⛔ — التحقق يقارن بمرجع آخر، الخلاف وهمي")
                    verdicts["آجل"] += 1
                else:
                    print("   ⇒ الفارق بين المرجعين غير حاسم لهذه الإشارة")
                    verdicts["غير حاسم"] += 1
            else:
                verdicts["لا بيانات"] += 1

        print("\n" + "=" * 100)
        print("الخلاصة")
        print("=" * 100)
        for k, v in verdicts.items():
            print(f"  {k}: {v}")
        print("\n  القرار المترتب:")
        print("   • غالبية 'فوري'  → الخلاف حقيقي، تصحيح صفوف المعادن مبرَّر.")
        print("   • غالبية 'آجل'   → مرجعان مختلفان، لا تُصحَّح؛ يُصلَح التحقق لا المحرك.")
        print("   • مختلطة        → المرجع غير ثابت بين الإشارات، وهو بحد ذاته")
        print("                      يفسّر الخلاف ويستلزم تسجيل price_source أولاً.")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
