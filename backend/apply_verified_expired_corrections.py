"""
apply_verified_expired_corrections.py
========================================
يصحّح فقط الصفوف EXPIRED (آخر 30 يوم) اللي أداة "🔍 تحقق من الكل"
(verify-outcome-bulk) قدرت تتحقق منها فعلياً مقابل بيانات سوق حقيقية —
detected في (TP1_HIT, TP2_HIT, SL_HIT, STILL_ACTIVE). أي صف طلع
NO_DATA يُستبعد تلقائياً من الفلترة نفسها — يبقى EXPIRED بدون أي لمس،
لأنه ما في دليل يوثّق حالته الحقيقية.

يستخدم نفس _verify_signal_outcome_core (شمعة-شمعة، الترتيب الزمني
الصحيح، admin.py) — نفس المنطق المؤكد صحته اليوم على الحالات الثلاث.

لكل صف مصحَّح:
  - TP1_HIT/TP2_HIT/SL_HIT: يصحّح status، يعيد حساب points_earned/
    profit_loss/profit_loss_percentage بالمستوى الحقيقي، يعلّم
    outcome_verified=True.
  - STILL_ACTIVE: يرجّع status=ACTIVE، points_earned=None،
    profit_loss=0.0، exit_executed=None (لسا ما انحسمت فعلياً).
    ⚠️ ملاحظة: لو expires_at الأصلي كان بالماضي، هالصف لسا ما رح
    يُفحص تلقائياً بعدها (bot_check_outcomes يفلتر expires_at > الآن)
    — هذا يُطبع تحذيراً منفصلاً، ما يُصلَّح هون (خارج نطاق الطلب).

⚠️ لا يلمس notes إطلاقاً (بطلب صريح: بدون أي أثر ظاهر للمستخدم/الأدمن
بالواجهة) — التوثيق فقط عبر لوق السيرفر (logger.info) ومخرجات هذا
السكربت نفسها وقت التشغيل. صفر إشعارات للمستخدمين.

⚠️ افتراضياً DRY-RUN. لازم --apply صراحة للتنفيذ الفعلي.

التشغيل:
  docker cp apply_verified_expired_corrections.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/apply_verified_expired_corrections.py            # dry-run
  docker exec moshapi_backend python /app/apply_verified_expired_corrections.py --apply     # تطبيق فعلي
"""
import sys, asyncio
sys.path.insert(0, "/app")

from datetime import datetime, timedelta, timezone
from loguru import logger
from app.database import SessionLocal
from app.models.signal import Signal, SignalStatus
from app.api.admin import _verify_signal_outcome_core, _calc_points

LOOKBACK_DAYS = 30
APPLICABLE = {"TP1_HIT", "TP2_HIT", "SL_HIT", "STILL_ACTIVE"}

# (2026-09-12) استثناء صريح — لا علاقة له بجودة _verify_signal_outcome_core:
# #2354 XAUUSD دخوله (4307.35) كان بق حارس سعر (أُصلح commit 12daaf7) —
# رقم لم يوجد إطلاقاً بالسوق الحقيقي، صُحِّح يدوياً لـEXPIRED عمداً لأن
# مستوياته (SL/TP) وهمية بالكامل. التحقق هون بيفحص "هل السعر الحقيقي لمس
# رقم الـSL المسجَّل؟" — وبالصدفة نعم (رقم عادي بمدى تداول الذهب)، فيرجّع
# نفس النتيجة الفاسدة (-513.68) اللي صححناها أصلاً. أي صف تاني عرفنا لاحقاً
# إن مستوياته وهمية لنفس السبب يُضاف هون.
EXCLUDE_IDS = {2354}


async def main():
    apply = "--apply" in sys.argv
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
        rows = (
            db.query(Signal)
            .filter(Signal.status == SignalStatus.EXPIRED, Signal.created_at >= cutoff)
            .all()
        )
        excluded = [s for s in rows if s.id in EXCLUDE_IDS]
        rows = [s for s in rows if s.id not in EXCLUDE_IDS]
        print(f"📊 صفوف EXPIRED آخر {LOOKBACK_DAYS} يوم: {len(rows) + len(excluded)}")
        if excluded:
            print(f"⛔ مستبعدة صراحة (مستويات وهمية معروفة، راجع EXCLUDE_IDS): "
                  f"{', '.join('#' + str(s.id) for s in excluded)}")

        fixed_win = fixed_loss = fixed_active = skipped_no_data = 0
        total_points_delta = 0.0
        created_dates = []

        for i, s in enumerate(rows):
            if i > 0:
                await asyncio.sleep(0.4)
            r = await _verify_signal_outcome_core(s)
            detected = r.get("detected")
            if detected not in APPLICABLE:
                skipped_no_data += 1
                continue

            old_status = s.status.value if hasattr(s.status, "value") else s.status
            old_points = s.points_earned or 0.0
            created_dates.append(s.created_at)

            if detected == "STILL_ACTIVE":
                new_points = None
                if apply:
                    s.status = SignalStatus.ACTIVE
                    s.points_earned = None
                    s.profit_loss = 0.0
                    s.exit_executed = None
                fixed_active += 1
                logger.info(f"[EXPIRED-FIX] #{s.id} {s.market} — {old_status}({old_points}) -> ACTIVE (لسا نشطة فعلياً) — {datetime.now(timezone.utc).isoformat()}")
                print(f"  #{s.id:5d} {s.market:10s} {s.timeframe:4s}  {old_status}({old_points}) → ACTIVE"
                      + ("" if apply else "  [DRY-RUN]")
                      + ("  ⚠️ expires_at بالماضي — لن يُفحص تلقائياً بعد الآن" if s.expires_at and s.expires_at < datetime.now(timezone.utc) else ""))
                continue

            new_status = SignalStatus(detected)
            entry = float(s.entry_price)
            sl    = float(s.stop_loss)
            tp1   = float(s.take_profit_1)
            tp2   = float(s.take_profit_2 or tp1)
            is_buy = (s.signal_type.value if hasattr(s.signal_type, "value") else s.signal_type) == "BUY"

            if new_status == SignalStatus.SL_HIT:
                diff, exit_price = abs(entry - sl), sl
            elif new_status == SignalStatus.TP2_HIT:
                diff, exit_price = abs(tp2 - entry), tp2
            else:
                diff, exit_price = abs(tp1 - entry), tp1

            points = _calc_points(s.market, diff, entry)
            if new_status == SignalStatus.SL_HIT:
                points = -points
                fixed_loss += 1
            else:
                fixed_win += 1
            pnl_pct = round((exit_price - entry) / entry * 100, 3) if is_buy \
                      else round((entry - exit_price) / entry * 100, 3)

            total_points_delta += (points - old_points)

            if apply:
                s.status = new_status
                s.points_earned = round(points, 2)
                s.profit_loss = round(points, 2)
                s.profit_loss_percentage = pnl_pct
                s.outcome_verified = True

            logger.info(f"[EXPIRED-FIX] #{s.id} {s.market} — {old_status}({old_points}) -> {detected}({points:+.2f}) — {datetime.now(timezone.utc).isoformat()}")
            print(f"  #{s.id:5d} {s.market:10s} {s.timeframe:4s}  {old_status}({old_points}) → {detected}({points:+.2f})"
                  + ("" if apply else "  [DRY-RUN]"))

        if apply:
            db.commit()

        print("\n" + "="*90)
        print(f"📊 النتيجة: رابحة مصحَّحة={fixed_win}  خاسرة مصحَّحة={fixed_loss}  "
              f"رجّعت ACTIVE={fixed_active}  تُركت EXPIRED (NO_DATA)={skipped_no_data}")
        print(f"📊 صافي التغيّر بمجموع النقاط (TP/SL فقط): {total_points_delta:+.2f}")
        if created_dates:
            created_dates.sort()
            print(f"📊 التوزيع الزمني للصفوف المصحَّحة: من {created_dates[0]} إلى {created_dates[-1]}")
            from collections import Counter
            by_day = Counter(d.date().isoformat() for d in created_dates)
            for day, cnt in sorted(by_day.items()):
                print(f"     {day}: {cnt} صف")
        print("="*90)
        if not apply:
            print("ℹ️  dry-run — لم يُعدَّل شيء. شغّل بـ--apply للتنفيذ الفعلي.")
        else:
            print(f"✅ تم تطبيق التصحيح.")

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
