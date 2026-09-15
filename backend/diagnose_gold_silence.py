"""
diagnose_gold_silence.py
===========================
تشخيص قراءة فقط (لا يحفظ أي إشارة، لا يعدّل أي صف) — يجاوب على سؤال
واحد: ليش XAUUSD ما أنتج ولا إشارة بآخر 3 أيام، بينما XAGUSD/XPTUSD
أنتجوا؟

الذهب موجود بقائمة market_scanner.SCAN_SYMBOLS (أول رمز فيها) ويُفحص
كل 30 دقيقة على 3 فريمات = ~144 محاولة يومياً. صفر إشارات بـ3 أيام
(~430 محاولة) يعني بوابة ما ترفضه بشكل منهجي، مش سوق هادئ.

يشغّل نفس analyze_market() الحقيقية (نفس ما يستدعيه bot_analyze/
الماسح) على XAUUSD و XAGUSD (الضابط — هو ينتج إشارات فعلاً) على
الفريمات الثلاثة، ويطبع لكل واحدة:
  - التوصية النهائية + سبب الرفض (rejection_reason) إن وُجد
  - المستويات قبل الرفض (_pre_reject_levels) — تكشف مسافة SL المقصودة
  - نسبة SL/entry مقابل سقف ATR (sl_cap_pct) — بوابة SL_DISTANCE_EXCEEDS_CAP
  - مدخلات حارس طزاجة السعر: السعر المستقل مقابل current_price والفجوة
    المسموحة ($20 للذهب / $0.60 للفضة)

وأخيراً: آخر إشارة XAUUSD بقاعدة البيانات (متى بالضبط).

التشغيل:
  docker cp diagnose_gold_silence.py moshapi_backend:/app/
  docker compose -f docker-compose.prod.yml exec backend python /app/diagnose_gold_silence.py
"""
import sys, asyncio
sys.path.insert(0, "/app")

from datetime import datetime, timezone

SYMBOLS    = ["XAUUSD", "XAGUSD"]
TIMEFRAMES = ["15m", "1h", "4h"]


async def main():
    from app.services.ai_engine_v5 import mosh_ai_engine_v5 as engine, _MAX_PRICE_GAP_USD
    from app.services.smart_data import smart_data
    from app.database import SessionLocal
    from app.models.signal import Signal

    print("=" * 96)
    print(f"تشخيص صمت الذهب — {datetime.now(timezone.utc).isoformat()}")
    print("=" * 96)

    # ⚠️ ضروري: هذا السكربت عملية مستقلة، وSmartData.__init__ يبدأ بـ
    # _td_enabled=False. بدون هذا السطر يقيس السكربت سلوكاً مختلفاً عن
    # سلوك السيرفر (TwelveData مطفأ) — وهذا أنتج تشخيصاً مضللاً فعلياً
    # بتاريخ 15/09 قبل اكتشاف السبب.
    td_ok = smart_data.restore_twelvedata_from_settings()
    print(f"  TwelveData (مصدر spot اللحظي): {'مفعّل ✅' if td_ok else 'غير مفعّل ⚠️'}")

    # ── 0) هل السوق مفتوح أصلاً؟ ─────────────────────────────────────────
    for sym in SYMBOLS:
        print(f"  is_market_open({sym}) = {smart_data.is_market_open(sym)}")

    # ── 1) السعر المستقل المستخدم بحارس الطزاجة ──────────────────────────
    print("\n" + "-" * 96)
    print("حارس طزاجة السعر — مدخلاته الحقيقية الآن")
    print("-" * 96)
    independent = {}
    for sym in SYMBOLS:
        try:
            p = engine._fetch_independent_check_price(sym)
        except Exception as e:
            p = 0.0
            print(f"  ⚠️ {sym}: _fetch_independent_check_price استثناء: {e}")
        independent[sym] = p
        # القيمة الفعلية المستخدمة بـ_validate_price_freshness وليست القيمة
        # الخام بالقاموس: للمعادن صارت max(الثابت، 1% من السعر) بعد إصلاح
        # الانجراف (15/09) — طباعة الخام وحدها كانت مضللة.
        fixed = _MAX_PRICE_GAP_USD.get(sym, 0.0)
        effective = max(fixed, p * 0.01) if p > 0 else fixed
        print(f"  {sym}: السعر المستقل = {p}   |   الحد الخام = {fixed}   |   "
              f"الحد الفعلي المطبَّق = {effective:.2f}"
              + (f"  ({effective / p * 100:.3f}% من السعر)" if p > 0 else "  ⚠️ صفر — المصدر المستقل غير متاح"))

    # ── 2) تشغيل التحليل الحقيقي ─────────────────────────────────────────
    for sym in SYMBOLS:
        print("\n" + "=" * 96)
        print(f"تحليل حقيقي: {sym}")
        print("=" * 96)
        for tf in TIMEFRAMES:
            try:
                a = await engine.analyze_market(symbol=sym, timeframe=tf, force_refresh=True)
            except Exception as e:
                print(f"  {tf:4s}  ❌ استثناء: {type(e).__name__}: {e}")
                continue

            rec        = a.get("recommendation")
            reason     = a.get("rejection_reason")
            conf       = a.get("ai_confidence_score")
            price      = a.get("current_price")
            src        = a.get("price_source")
            levels     = a.get("levels") or {}
            pre        = a.get("_pre_reject_levels") or {}
            pre_rec    = a.get("_pre_reject_rec")

            print(f"\n  ── {sym} / {tf} ──")
            print(f"     التوصية: {rec}   الثقة: {conf}   السعر: {price}  (مصدر: {src})")
            if reason:
                print(f"     ⛔ سبب الرفض: {reason}   (التوصية قبل الرفض: {pre_rec})")

            use = levels or pre
            entry = use.get("entry") or (a.get("entry_zones") or [None])[0]
            sl    = use.get("stop_loss") or a.get("stop_loss_zone")
            if entry and sl:
                try:
                    entry_f, sl_f = float(entry), float(sl)
                    sl_pct = abs(entry_f - sl_f) / entry_f
                    # نفس صيغة البوابة بالضبط (ai_engine_v5.py:2398-2400):
                    # ATR يُقرأ من levels نفسها، لا من جذر analysis
                    atr = float(use.get("atr") or 0)
                    cap = max(0.005, (atr / entry_f) * 1.0) if atr > 0 else 0.005
                    verdict = "تتجاوز السقف ⛔" if sl_pct > cap else "ضمن السقف ✅"
                    print(f"     مسافة SL: {sl_pct*100:.4f}%   سقف ATR: {cap*100:.4f}%   (ATR={atr}) → {verdict}")
                except Exception as e:
                    print(f"     (تعذّر حساب مسافة SL: {e})")
            else:
                print(f"     (لا توجد مستويات — levels فارغة و_pre_reject_levels فارغة)")

            await asyncio.sleep(2)

    # ── 3) آخر إشارة ذهب فعلية بقاعدة البيانات ───────────────────────────
    print("\n" + "=" * 96)
    print("آخر إشارات XAUUSD المحفوظة فعلياً")
    print("=" * 96)
    db = SessionLocal()
    try:
        rows = (db.query(Signal)
                  .filter(Signal.market == "XAUUSD")
                  .order_by(Signal.created_at.desc())
                  .limit(5).all())
        if not rows:
            print("  ⚠️ لا توجد أي إشارة XAUUSD بقاعدة البيانات إطلاقاً.")
        for s in rows:
            age_h = (datetime.now(timezone.utc) - (s.created_at.replace(tzinfo=timezone.utc)
                     if s.created_at.tzinfo is None else s.created_at)).total_seconds() / 3600
            status = s.status.value if hasattr(s.status, "value") else s.status
            print(f"  #{s.id}  {s.timeframe:4s}  {status:9s}  دخول={s.entry_price}  "
                  f"أُنشئت={s.created_at}  (قبل {age_h:.1f} ساعة)")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
