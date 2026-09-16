"""
migrate_add_strategy_diagnostics.py
======================================
يضيف عمود diagnostics_json إلى strategy_trigger_events.

create_all() ينشئ الجداول الجديدة تلقائياً ولا يضيف أعمدة لجدول قائم —
فالعمود يحتاج ALTER TABLE صريحاً. idempotent: إعادة التشغيل لا تضر.

الغرض: تخزين سبب عدم إطلاق الاستراتيجية لحظة التقييم. بلاغ حقيقي
(17/09): عتبة مضبوطة على 50 وسجلّ يعرض "Score 54" مراراً بلا إطلاق،
فبدا الأمر عطلاً — والسبب أن الإطلاق يشترط منطق المجموعات **مع** العتبة،
وكان السجل يعرض العتبة وحدها. والسبب لا يُعاد حسابه لاحقاً لأن حالة
السوق تغيّرت، فيلزم تخزينه لحظتها.

التشغيل:
  docker cp migrate_add_strategy_diagnostics.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/migrate_add_strategy_diagnostics.py
"""
import sys
sys.path.insert(0, "/app")

from sqlalchemy import text
from app.database import engine

TABLE = "strategy_trigger_events"
COLUMN = "diagnostics_json"


def main():
    print("=" * 70)
    print(f"هجرة: {TABLE}.{COLUMN}")
    print("=" * 70)

    with engine.begin() as conn:
        tbl = conn.execute(text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = :t"
        ), {"t": TABLE}).fetchone()
        if not tbl:
            print(f"  ℹ️  جدول {TABLE} غير موجود — سيُنشئه create_all كاملاً.")
            return

        exists = conn.execute(text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ), {"t": TABLE, "c": COLUMN}).fetchone()

        if exists:
            print(f"  ✅ {COLUMN} موجود مسبقاً — لا تغيير.")
        else:
            conn.execute(text(f"ALTER TABLE {TABLE} ADD COLUMN IF NOT EXISTS {COLUMN} JSONB"))
            print(f"  ➕ أُضيف {COLUMN}.")

        n = conn.execute(text(f"SELECT COUNT(*) FROM {TABLE}")).scalar()
        print(f"\n  أحداث موجودة: {n}")
        print("  ⚠️ الأحداث السابقة تبقى بلا سبب مخزَّن — لا يمكن استنتاجه")
        print("     بأثر رجعي لأن حالة السوق وقتها غير متاحة. السبب يظهر")
        print("     للأحداث الجديدة فقط.")

    print("\n✅ انتهت الهجرة. أعد تشغيل الـbackend.")


if __name__ == "__main__":
    main()
