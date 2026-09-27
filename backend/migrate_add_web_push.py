"""
migrate_add_web_push.py
========================================
(2026-09-27) إشعارات المتصفح (Web Push) — قناة موازية لتيليجرام تصل حتى
عميل ما ربط حسابه بتيليجرام إطلاقاً. جدول push_subscriptions جديد بالكامل
(يُنشأ تلقائياً بأول تشغيل للـbackend بعد هذا التحديث — بلا migration يدوي
له). هذا الملف يضيف عموداً واحداً فقط على جدول signals الموجود مسبقاً.

التشغيل:
  docker cp migrate_add_web_push.py moshapi_backend:/app/
  docker compose -f docker-compose.prod.yml exec backend python /app/migrate_add_web_push.py
"""
import sys
sys.path.insert(0, "/app")
from app.database import engine
from sqlalchemy import text


def migrate():
    with engine.connect() as conn:
        try:
            conn.execute(text(
                "ALTER TABLE signals ADD COLUMN push_broadcast_sent BOOLEAN DEFAULT FALSE"
            ))
            conn.commit()
            print("✅ Column signals.push_broadcast_sent added")
        except Exception as e:
            conn.rollback()
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print("ℹ️  Column signals.push_broadcast_sent already exists — skipping")
            else:
                print(f"❌ Error adding column: {e}")
                raise


if __name__ == "__main__":
    migrate()
