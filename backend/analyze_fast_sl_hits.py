"""
analyze_fast_sl_hits.py
=========================
تشخيص قراءة فقط (لا تعديل) — يحدد صفقات SL_HIT/TP_HIT احتُسبت خلال دقائق
قليلة من إنشائها، وهي على الأغلب ضحايا بق range_check غير المفلتر زمنياً
(أُصلح 2026-09-11 في bot.py::bot_check_outcomes — كان يفحص آخر 2.5 ساعة
من الشموع بدون فلترة created_at، فأي لمسة تاريخية قبل وجود الإشارة كانت
تُنسب لها غلطاً كـ"ضربت الآن").

يطبع كل صفقة أُغلقت خلال أقل من N دقيقة من إنشائها (افتراضياً 5) — هذي
مرشّحة للتصحيح اليدوي (تحويل لـEXPIRED) لأنها غالباً نتيجة البق، مو صفقة
حقيقية ضُربت بهالسرعة.

التشغيل (قراءة فقط، آمن 100%):
  docker cp analyze_fast_sl_hits.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/analyze_fast_sl_hits.py
"""
import sys
sys.path.insert(0, "/app")

from datetime import datetime, timedelta, timezone
from app.database import SessionLocal
from app.models.signal import Signal, SignalStatus

FAST_MINUTES = 5           # عتبة "سريع جداً بشكل غير طبيعي"
LOOKBACK_DAYS = 14         # نطاق الفحص


def main():
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
            .order_by(Signal.created_at.desc())
            .all()
        )
        print(f"📊 صفقات محسومة آخر {LOOKBACK_DAYS} يوم: {len(rows)}")

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

        print(f"\n{'='*90}")
        print(f"⚠️  صفقات أُغلقت خلال أقل من {FAST_MINUTES} دقائق من إنشائها ({len(suspects)} صفقة):")
        print(f"{'='*90}")
        for s, minutes in sorted(suspects, key=lambda x: x[1]):
            status = s.status.value if hasattr(s.status, "value") else s.status
            print(f"  #{s.id:5d}  {s.market:10s} {s.timeframe:4s}  {status:8s}  "
                  f"points={s.points_earned or 0:+8.2f}  "
                  f"أُنشئت={created_str(s.created_at)}  أُغلقت={created_str(s.exit_executed)}  "
                  f"خلال {minutes:.1f} دقيقة")

        if suspects:
            print(f"\n💡 هذي مرشّحة للتصحيح (تحويل لـEXPIRED) لأنها على الأغلب نتيجة")
            print(f"   البق يلي انصلح بـcommit c2f6cb8 — راجعها وقرر أي واحدة تصحّحها فعلياً.")
        else:
            print("\n✅ لا يوجد صفقات مشبوهة بهالمعيار.")

    finally:
        db.close()


def created_str(dt):
    if not dt:
        return "—"
    return dt.strftime("%Y-%m-%d %H:%M")


if __name__ == "__main__":
    main()
