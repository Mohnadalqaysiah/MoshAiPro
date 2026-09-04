"""
migrate_recalc_points.py
========================
يُعيد حساب points_earned لجميع الإشارات المغلقة (TP1/TP2/SL) باستخدام
_calc_points() الحيّة الحقيقية من app/api/admin.py (مستوردة مباشرة، مش
نسخة محلية) — أي تصحيح مستقبلي على الجدول هناك ينعكس هون تلقائياً.

⚠️ تحذير قبل التشغيل: هذا السكربت يعيد كتابة points_earned/profit_loss
لكل صفقة مغلقة بكل النظام (كل المستخدمين). شغّله فقط بعد تأكيد صريح
من المستخدم إنه فعلاً يريد إعادة حساب البيانات التاريخية — مو تلقائياً
كجزء من أي نشر عادي.

(2026-09-04) اكتُشف إن الأسهم الأمريكية الفردية (AAPL/GOOGL/...) كانت
تسقط بدون تصنيف على مضاعف الفوركس ×10000 غلطاً — أُصلح بـ_calc_points
نفسها (×1، بمعاملة المؤشرات/الكريبتو). صفوف من أبريل 2026 لسا فيها
الأثر القديم (~22 صف تاريخي، مستبعدة حالياً من bot_user_stats تلقائياً
لأنها current_price=NULL) — تشغيل هالسكربت هو الطريقة الصحيحة لتصحيحها
رجعياً لو قرر المستخدم هيك.

التشغيل:
  docker cp migrate_recalc_points.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/migrate_recalc_points.py
"""
import sys, os
sys.path.insert(0, "/app")

from app.database import SessionLocal
from app.models.signal import Signal, SignalStatus

# (2026-09-04) كانت هون نسخة محلية مستقلة من _calc_points بمعادلة قديمة
# جداً (معادن ×100 بدل ×10 الحالي، ولا فئة إطلاقاً للمؤشرات/الأسهم
# الأمريكية/الأسهم الخليجية — كلهم كانوا يسقطوا على ×10000 الفوركس
# غلطاً). لو هالسكربت انشغّل بهيئته القديمة كان رح يعيد كتابة
# points_earned لكل صفقة مغلقة بكل النظام بأرقام غلط. صار يستورد
# الدالة الحقيقية الوحيدة من admin.py (نفس مبدأ decision_grouping.py
# المشترك) بدل نسخة محلية قابلة للتقادم بصمت.
from app.api.admin import _calc_points


def recalc():
    db = SessionLocal()
    closed = [SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT]

    signals = db.query(Signal).filter(Signal.status.in_(closed)).all()
    print(f"📊 Found {len(signals)} closed signals to recalculate")

    updated = skipped = errors = 0

    for s in signals:
        try:
            entry = s.entry_price
            sl    = s.stop_loss
            tp1   = s.take_profit_1
            tp2   = s.take_profit_2

            if not entry:
                skipped += 1
                continue

            status = s.status.value if hasattr(s.status, 'value') else str(s.status)

            if status == "TP1_HIT":
                diff   = abs((tp1 or entry) - entry)
                points = _calc_points(s.market, diff)

            elif status == "TP2_HIT":
                diff   = abs((tp2 or tp1 or entry) - entry)
                points = _calc_points(s.market, diff)

            elif status == "SL_HIT":
                diff   = abs((sl or entry) - entry)
                points = -_calc_points(s.market, diff)

            else:
                skipped += 1
                continue

            old_pts = s.points_earned or 0
            s.points_earned = points
            s.profit_loss   = points

            print(f"  Signal #{s.id:4d}  {s.market or '?':8s}  {status:8s}  "
                  f"old={old_pts:>10.2f}  new={points:>10.2f}  "
                  f"{'✅ CHANGED' if abs(old_pts - points) > 0.01 else '— same'}")
            updated += 1

        except Exception as e:
            print(f"  ⚠️  Signal #{s.id} error: {e}")
            errors += 1

    db.commit()
    db.close()

    print(f"\n{'='*60}")
    print(f"✅ Done: {updated} recalculated, {skipped} skipped, {errors} errors")
    print(f"{'='*60}")


if __name__ == "__main__":
    recalc()
