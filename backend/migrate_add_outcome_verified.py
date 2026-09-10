"""
migrate_add_outcome_verified.py
================================
(2026-09-10) يضيف عمود outcome_verified (Boolean) لجدول signals.

الغرض: تمييز التصحيح اليدوي **المؤكد بالسعر الحقيقي** (زر "تحقق" +
تحقّق closed_price بـset_signal_outcome — وصل المستوى فعلاً) عن التصحيح
اليدوي القديم غير المؤكد. verified_unique_decisions صار يشمل الاثنين
(تلقائي + مؤكد) بتقارير الأداء والصفحة العامة، بدل استبعاد كل تصحيح
يدوي. معايرة المحرك (load_performance_from_db) تبقى صارمة على التلقائي.

Backfill: يضبط outcome_verified=True للإشارات المغلقة يدوياً حديثاً
(current_price IS NULL و exit_executed خلال آخر 3 أيام) — لأن هاي هي
اللي صُحّحت بزر التحقق الجديد بهاي الفترة. الصفوف الأقدم (خلل تاريخي
من أبريل-أغسطس) تبقى False.

التشغيل:
  docker cp migrate_add_outcome_verified.py moshapi_backend:/app/
  docker compose -f docker-compose.prod.yml exec backend python /app/migrate_add_outcome_verified.py
"""
import sys
sys.path.insert(0, "/app")
from datetime import datetime, timedelta, timezone
from app.database import engine
from sqlalchemy import text


def migrate():
    # 1) إضافة العمود (idempotent)
    with engine.connect() as conn:
        try:
            conn.execute(text(
                "ALTER TABLE signals ADD COLUMN outcome_verified BOOLEAN DEFAULT FALSE"
            ))
            conn.commit()
            print("✅ Column outcome_verified added")
        except Exception as e:
            conn.rollback()
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print("ℹ️  Column outcome_verified already exists — skipping")
            else:
                print(f"❌ Error adding column: {e}")
                raise

    # 2) Backfill: التصحيحات اليدوية الحديثة (آخر 3 أيام) = مؤكدة
    cutoff = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    with engine.connect() as conn:
        try:
            res = conn.execute(text("""
                UPDATE signals
                SET outcome_verified = TRUE
                WHERE status IN ('TP1_HIT', 'TP2_HIT', 'SL_HIT')
                  AND current_price IS NULL
                  AND exit_executed IS NOT NULL
                  AND exit_executed >= :cutoff
                  AND (outcome_verified IS NULL OR outcome_verified = FALSE)
            """), {"cutoff": cutoff})
            conn.commit()
            print(f"✅ Backfilled outcome_verified=TRUE for {res.rowcount} recent manual corrections (since {cutoff[:10]})")
        except Exception as e:
            conn.rollback()
            print(f"❌ Backfill error: {e}")
            raise


if __name__ == "__main__":
    migrate()
