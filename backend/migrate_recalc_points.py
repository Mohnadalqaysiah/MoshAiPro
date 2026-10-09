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

(2026-10-09) صار DRY-RUN افتراضياً: يطبع فقط الصفوف التي سيتغيّر رقمها
(قديم → جديد) وملخّصاً لكل رمز، بدون أي كتابة. التنفيذ الفعلي بـ--apply
صراحة. السبب: جدول النقاط تغيّر (حجم نقطة لكل أداة) وصاحب المشروع طلب
رؤية الفرق قبل اعتماده.

(2026-09-04) اكتُشف إن الأسهم الأمريكية الفردية (AAPL/GOOGL/...) كانت
تسقط بدون تصنيف على مضاعف الفوركس ×10000 غلطاً — أُصلح بـ_calc_points
نفسها. تشغيل هالسكربت هو الطريقة الصحيحة لتصحيحها رجعياً لو قرر
المستخدم هيك.

التشغيل:
  docker cp migrate_recalc_points.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/migrate_recalc_points.py            # معاينة فقط
  docker exec moshapi_backend python /app/migrate_recalc_points.py --apply    # تطبيق فعلي
"""
import sys
from collections import defaultdict
sys.path.insert(0, "/app")

from app.database import SessionLocal
from app.models.signal import Signal, SignalStatus

# (2026-09-04) يستورد الدالة الحقيقية الوحيدة من admin.py بدل نسخة محلية
# قابلة للتقادم بصمت.
from app.api.admin import _calc_points


def recalc(apply: bool):
    db = SessionLocal()
    closed = [SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT]

    signals = db.query(Signal).filter(Signal.status.in_(closed)).order_by(Signal.market, Signal.id).all()
    print(f"📊 صفقات مغلقة: {len(signals)}  —  {'تطبيق فعلي' if apply else 'معاينة فقط (DRY-RUN)'}\n")

    changed = same = skipped = errors = 0
    # لكل رمز: عدد الصفوف المتغيّرة، مجموع القديم، مجموع الجديد، مثال
    per_market = defaultdict(lambda: {"n": 0, "old": 0.0, "new": 0.0, "example": None})

    for s in signals:
        try:
            entry = s.entry_price
            if not entry:
                skipped += 1
                continue

            status = s.status.value if hasattr(s.status, 'value') else str(s.status)
            if status == "TP1_HIT":
                diff   = abs((s.take_profit_1 or entry) - entry)
                points = _calc_points(s.market, diff, entry)
            elif status == "TP2_HIT":
                diff   = abs((s.take_profit_2 or s.take_profit_1 or entry) - entry)
                points = _calc_points(s.market, diff, entry)
            elif status == "SL_HIT":
                diff   = abs((s.stop_loss or entry) - entry)
                points = -_calc_points(s.market, diff, entry)
            else:
                skipped += 1
                continue

            old_pts = s.points_earned or 0
            if abs(old_pts - points) <= 0.01:
                same += 1
                continue

            changed += 1
            m = per_market[s.market or "?"]
            m["n"] += 1
            m["old"] += old_pts
            m["new"] += points
            if m["example"] is None:
                m["example"] = (s.id, status, entry, diff, old_pts, points)

            print(f"  #{s.id:5d}  {s.market or '?':10s}  {status:8s}  "
                  f"فرق السعر={diff:<12.6g}  قديم={old_pts:>10.2f}  →  جديد={points:>10.2f}")

            if apply:
                s.points_earned = points
                s.profit_loss   = points

        except Exception as e:
            print(f"  ⚠️  Signal #{s.id} error: {e}")
            errors += 1

    print(f"\n{'='*90}\nملخّص لكل رمز (الصفوف المتغيّرة فقط):")
    for mk, m in sorted(per_market.items()):
        sid, st, entry, diff, o, n = m["example"]
        print(f"  {mk:10s}  صفوف={m['n']:4d}  مجموع قديم={m['old']:>12.2f}  مجموع جديد={m['new']:>12.2f}"
              f"   مثال #{sid} {st} دخول={entry} فرق={diff:.6g}: {o:.2f} → {n:.2f}")

    print(f"\n{'='*90}")
    print(f"ستتغيّر: {changed}   بلا تغيير: {same}   متخطّاة: {skipped}   أخطاء: {errors}")
    if apply:
        db.commit()
        print("✅ تم التطبيق.")
    else:
        print("ℹ️  معاينة فقط — لم يُكتب شيء. للتطبيق: --apply")
    print('='*90)
    db.close()


if __name__ == "__main__":
    recalc(apply="--apply" in sys.argv)
