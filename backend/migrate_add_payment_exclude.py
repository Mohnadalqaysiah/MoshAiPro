"""
migrate_add_payment_exclude.py
========================================
(2026-10-04) عمود payments.exclude_from_stats — يستبعد دفعات تجريبية/اختبارية
من إحصائيات لوحة الإدارة (الإيرادات وعدد الاشتراكات) بدون حذف السجل.

التشغيل:
  docker cp backend/migrate_add_payment_exclude.py moshapi_backend:/app/
  docker compose -f docker-compose.prod.yml exec backend python /app/migrate_add_payment_exclude.py
"""
import sys
sys.path.insert(0, "/app")
from app.database import engine
from sqlalchemy import text


def migrate():
    with engine.connect() as conn:
        try:
            conn.execute(text(
                "ALTER TABLE payments ADD COLUMN exclude_from_stats BOOLEAN NOT NULL DEFAULT FALSE"
            ))
            conn.commit()
            print("✅ Column payments.exclude_from_stats added")
        except Exception as e:
            conn.rollback()
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print("ℹ️  Column payments.exclude_from_stats already exists — skipping")
            else:
                print(f"❌ Error adding column: {e}")
                raise


if __name__ == "__main__":
    migrate()
