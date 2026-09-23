"""
fix_signal_2611.py
========================================
تصحيح يدوي لحالة واحدة صريحة (بطلب مباشر من صاحب المنتج، بلا مسح تاريخي
عام — راجع DECISIONS.md 2026-09-24): إشارة #2611 (XAGUSD BUY، دخول
64.4575) سُجّلت SL_HIT بالكود القديم المعطوب (قبل بوابة entry_executed)
رغم أن الصفقة تفعّلت فعلاً لاحقاً ولسا مفتوحة حسب تأكيد مباشر من
MetaTrader الحقيقي. تُصحَّح إلى EXPIRED مؤقتاً (لا SL_HIT خاطئة، ولا
TP/SL بعد لأن النتيجة الحقيقية لسا غير معروفة) — تُسجَّل النتيجة النهائية
يدوياً لاحقاً (ربح أو خسارة) بمجرد ما تتأكد فعلياً.

⚠️ افتراضياً DRY-RUN. لازم --apply صراحة للتنفيذ الفعلي.

التشغيل:
  docker cp fix_signal_2611.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/fix_signal_2611.py            # dry-run
  docker exec moshapi_backend python /app/fix_signal_2611.py --apply    # تطبيق فعلي
"""
import sys
sys.path.insert(0, "/app")

from datetime import datetime, timezone
from loguru import logger
from app.database import SessionLocal
from app.models.signal import Signal, SignalStatus

SIGNAL_ID = 2611


def main():
    apply = "--apply" in sys.argv
    db = SessionLocal()
    try:
        sig = db.query(Signal).filter(Signal.id == SIGNAL_ID).first()
        if not sig:
            print(f"❌ إشارة #{SIGNAL_ID} غير موجودة")
            return

        old_status = sig.status.value if hasattr(sig.status, "value") else sig.status
        old_points = sig.points_earned

        print(f"#{sig.id} {sig.market} {sig.timeframe} — الحالة الحالية: {old_status} ({old_points} نقطة)")
        print(f"  دخول={sig.entry_price}  SL={sig.stop_loss}  TP1={sig.take_profit_1}")
        print(f"  → سيُصحَّح إلى: EXPIRED (بانتظار تسجيل النتيجة الحقيقية يدوياً لاحقاً)")

        if apply:
            sig.status = SignalStatus.EXPIRED
            sig.points_earned = None
            sig.profit_loss = 0.0
            sig.profit_loss_percentage = 0.0
            sig.exit_executed = None
            sig.outcome_verified = False
            db.commit()
            logger.info(
                f"[MANUAL-FIX] #{sig.id} {sig.market} — {old_status}({old_points}) -> EXPIRED "
                f"(بلاغ مباشر: تفعّلت فعلاً بعد الإصلاح، MetaTrader يؤكد استمرارها) — "
                f"{datetime.now(timezone.utc).isoformat()}"
            )
            print("✅ تم التطبيق.")
        else:
            print("ℹ️  dry-run — لم يُعدَّل شيء. شغّل بـ--apply للتنفيذ الفعلي.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
