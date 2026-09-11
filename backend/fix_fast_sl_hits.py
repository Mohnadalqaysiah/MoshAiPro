"""
fix_fast_sl_hits.py
=====================
يصحّح صفقات TP/SL انحسمت خلال دقائق قليلة من إنشائها — ضحايا بق
range_check غير المفلتر زمنياً (أُصلح 2026-09-11، commit c2f6cb8).
نفس معيار الكشف بالضبط المستخدم بـanalyze_fast_sl_hits.py (قراءة فقط).

التصحيح: تحويل الحالة لـEXPIRED (points=0) — نفس المعاملة يلي طبّقناها
يدوياً على صفقة الذهب #2354. EXPIRED مستثناة تلقائياً من كل تقرير أداء
بالنظام (الموقع العام، البوت، لوحة الأدمن، تحليلات المستخدم) — راجع
grep على "SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT"
عبر المشروع، تأكيد إنها القائمة الوحيدة المحتسبة بكل مكان.

⚠️ افتراضياً DRY-RUN (يعرض بس، ما يكتب شي). لازم --apply صراحة للتنفيذ
الفعلي.

التشغيل:
  docker cp fix_fast_sl_hits.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/fix_fast_sl_hits.py            # dry-run
  docker exec moshapi_backend python /app/fix_fast_sl_hits.py --apply    # تطبيق فعلي
"""
import sys
sys.path.insert(0, "/app")

from datetime import datetime, timedelta, timezone
from app.database import SessionLocal
from app.models.signal import Signal, SignalStatus

FAST_MINUTES = 5
LOOKBACK_DAYS = 14


def main():
    apply = "--apply" in sys.argv
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
        rows = (
            db.query(Signal)
            .filter(
                Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT]),
                Signal.created_at >= cutoff,
                Signal.exit_executed.isnot(None),
            )
            .all()
        )

        suspects = []
        for s in rows:
            created = s.created_at
            exited  = s.exit_executed
            if created and created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if exited and exited.tzinfo is None:
                exited = exited.replace(tzinfo=timezone.utc)
            if not created or not exited:
                continue
            minutes = (exited - created).total_seconds() / 60
            if 0 <= minutes < FAST_MINUTES:
                suspects.append((s, minutes))

        suspects.sort(key=lambda x: x[1])
        print(f"📊 {len(suspects)} صفقة مرشّحة للتصحيح (أُغلقت خلال أقل من {FAST_MINUTES} دقائق من إنشائها):\n")

        for s, minutes in suspects:
            status = s.status.value if hasattr(s.status, "value") else s.status
            old_pts = s.points_earned or 0
            print(f"  #{s.id:5d}  {s.market:10s} {s.timeframe:4s}  {status:8s}  "
                  f"points={old_pts:+8.2f}  خلال {minutes:.1f} دقيقة"
                  + ("  → EXPIRED" if apply else "  (dry-run — لن يُعدَّل)"))
            if apply:
                s.status         = SignalStatus.EXPIRED
                s.points_earned  = 0
                s.profit_loss    = 0
                s.notes = (s.notes or "") + " [أُبطلت تلقائياً: ضحية بق range_check غير المفلتر زمنياً — أُصلح 2026-09-11]"

        if apply and suspects:
            db.commit()
            print(f"\n✅ تم تصحيح {len(suspects)} صفقة (status=EXPIRED, points=0).")
        elif not apply:
            print(f"\nℹ️  هذا dry-run — لم يُعدَّل شيء. شغّل بـ --apply للتنفيذ الفعلي.")
        else:
            print("\n✅ لا يوجد شيء للتصحيح.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
