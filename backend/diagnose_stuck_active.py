"""
diagnose_stuck_active.py
===========================
قراءة محضة — لا يعدّل صفاً ولا يغلق إشارة.

السؤال: لماذا تبقى إشارات ACTIVE بينما أداة التحقق تؤكد أنها ضربت الوقف؟

سبق أن شُخّص السبب بأنه شرط `walked` (نافذة المشي أقصر من عمر الإشارة)
وأُصلح — ولم تُغلق الإشارات بعد الإصلاح. فالتشخيص كان ناقصاً، ولا يصحّ
تخمين سبب ثانٍ بعد أن أخطأ الأول. هذه الأداة تعيد تنفيذ منطق
bot_check_outcomes خطوة بخطوة على كل إشارة نشطة، وتطبع **عند أي خطوة
بالضبط** ينقطع المسار:

  1) is_market_open      → السوق مغلق ⇒ تُتخطّى الإشارة كلياً
  2) مصدر السعر اللحظي   → لأي رمز، ومن أين، وهل نجح
  3) مقارنة السعر        → هل يتجاوز المستوى فعلاً الآن

المرشّحان القائمان قبل القياس:
  • السوق مغلق لرموز غير الكريبتو (أسهم سعودية/أمريكية، نفط، مؤشرات).
  • تغيير 16/09 قصر _SPOT_SYMBOLS على المعادن، فصارت بقية الرموز تأخذ
    سعرها اللحظي من get_realtime_price_with_meta بدل كاش TradingView —
    وهو مسار أثقل يُقيَّد معدله عند فحص عشرات الرموز كل 90 ثانية،
    فيُرجع None ويُتخطّى الصف بصمت (`if not price: continue`).

الفرق بينهما حاسم: الأول سلوك صحيح ينتظر فتح السوق، والثاني عطل يمنع
الرصد أصلاً.

التشغيل:
  docker cp diagnose_stuck_active.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/diagnose_stuck_active.py
"""
import sys, asyncio
sys.path.insert(0, "/app")

from datetime import datetime, timezone
from collections import Counter


async def main():
    from app.database import SessionLocal
    from app.models.signal import Signal, SignalStatus
    from app.services.smart_data import smart_data as _sd
    from app.services import ai_engine_v5 as _eng
    from app.services.tv_price_feed import TV_SYMBOL_MAP, tv_feed

    mosh = getattr(_eng, "mosh_ai_engine_v5", None)

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        active = (db.query(Signal)
                    .filter(Signal.status == SignalStatus.ACTIVE,
                            Signal.expires_at > now)
                    .order_by(Signal.created_at.desc()).all())

        print("=" * 98)
        print(f"تشخيص الإشارات العالقة — {len(active)} إشارة نشطة غير منتهية")
        print("=" * 98)
        print(f"  الوقت الآن: {now:%Y-%m-%d %H:%M} UTC")
        print(f"  كاش TradingView حيّ: {getattr(tv_feed, 'alive', '?')}\n")

        reasons = Counter()
        rows = []

        for sig in active:
            sym = sig.market.upper()
            step, detail = "", ""

            # ── 1) السوق مفتوح؟ ────────────────────────────────────────
            try:
                open_ = _sd.is_market_open(sig.market)
            except Exception as e:
                open_ = None
                detail = f"is_market_open رمى: {type(e).__name__}"
            if open_ is False:
                reasons["السوق مغلق — تُتخطّى"] += 1
                rows.append((sig, "1-السوق مغلق", "", None))
                continue
            if open_ is None:
                reasons["is_market_open فشل"] += 1
                rows.append((sig, "1-فشل فحص السوق", detail, None))
                continue

            # ── 2) السعر اللحظي — بنفس ترتيب bot_check_outcomes ────────
            price, src = None, ""
            if sym in ("XAUUSD", "XAGUSD"):
                try:
                    p = tv_feed.get_price_sync(sym)
                    if p and float(p) > 0:
                        price, src = float(p), "TV"
                    elif mosh:
                        raw, _ = mosh._fetch_spot_price(sym)
                        if raw and float(raw) > 0:
                            price, src = float(raw), "carry"
                except Exception as e:
                    detail = f"{type(e).__name__}: {e}"
            else:
                try:
                    info = await _sd.get_realtime_price_with_meta(sig.market)
                    if info and info.get("price"):
                        price, src = float(info["price"]), info.get("source", "?")
                except Exception as e:
                    detail = f"{type(e).__name__}: {e}"

            if not price:
                # هل كان كاش TV سيعطي سعراً لو استُخدم؟ يحسم المرشّح الثاني.
                tv_alt = None
                if sym in TV_SYMBOL_MAP:
                    try:
                        p = tv_feed.get_price_sync(sym)
                        tv_alt = float(p) if p and float(p) > 0 else None
                    except Exception:
                        pass
                reasons["تعذّر جلب السعر اللحظي"] += 1
                rows.append((sig, "2-لا سعر", detail or "—", tv_alt))
                continue

            # ── 3) المقارنة ────────────────────────────────────────────
            entry = float(sig.entry_price); sl = float(sig.stop_loss)
            tp1 = float(sig.take_profit_1); tp2 = float(sig.take_profit_2 or tp1)
            is_buy = (sig.signal_type.value if hasattr(sig.signal_type, "value")
                      else sig.signal_type) == "BUY"
            if is_buy:
                hit = ("SL" if price <= sl else "TP2" if price >= tp2
                       else "TP1" if price >= tp1 else None)
            else:
                hit = ("SL" if price >= sl else "TP2" if price <= tp2
                       else "TP1" if price <= tp1 else None)

            if hit:
                reasons[f"يجب أن تُغلق الآن ({hit})"] += 1
                rows.append((sig, f"3-يجب الإغلاق {hit}", f"{src} {price:g}", None))
            else:
                reasons["لم يتجاوز أي مستوى بعد"] += 1
                rows.append((sig, "3-لم تُلمس", f"{src} {price:g}", None))

        # ── التقرير ────────────────────────────────────────────────────
        print("-" * 98)
        print(f"  {'#':<6}{'الرمز':<10}{'النوع':<6}{'أُنشئت':<13}{'أين توقّف':<22}تفصيل")
        print("-" * 98)
        for sig, step, detail, tv_alt in rows:
            c = sig.created_at
            if c and c.tzinfo is None:
                c = c.replace(tzinfo=timezone.utc)
            extra = detail
            if tv_alt:
                extra += f"   ⚠️ كاش TV كان سيعطي {tv_alt:g}"
            print(f"  {sig.id:<6}{sig.market:<10}"
                  f"{(sig.signal_type.value if hasattr(sig.signal_type,'value') else sig.signal_type):<6}"
                  f"{c:%m-%d %H:%M}   {step:<22}{extra}")

        print("\n" + "=" * 98)
        print("الخلاصة")
        print("=" * 98)
        for k, v in reasons.most_common():
            print(f"  {k}: {v}")

        no_price = reasons.get("تعذّر جلب السعر اللحظي", 0)
        closed   = reasons.get("السوق مغلق — تُتخطّى", 0)
        print("\n  القرار المترتب:")
        if no_price:
            print(f"   ⛔ {no_price} إشارة بلا سعر لحظي — عطل بمصدر السعر لا بالمنطق.")
            print("      إن ظهر '⚠️ كاش TV كان سيعطي ...' فالسبب مؤكد: قصر")
            print("      _SPOT_SYMBOLS على المعادن نقل بقية الرموز لمسار أثقل")
            print("      يُقيَّد معدله. الإصلاح: فصل مصدر السعر اللحظي (TV لكل")
            print("      رمز متاح) عن مصدر شموع المشي (المعادن فقط).")
        if closed:
            print(f"   ℹ️ {closed} إشارة سوقها مغلق — سلوك صحيح، تُفحص عند الفتح.")
        if not no_price and not closed:
            print("   ✅ المسار سليم لكل إشارة — السبب خارج هذه الحلقة")
            print("      (تحقق أن البوت يستدعي /bot/check-outcomes فعلاً).")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
