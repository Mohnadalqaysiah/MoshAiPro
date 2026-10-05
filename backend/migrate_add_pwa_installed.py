"""
migrate_add_pwa_installed.py
========================================
(2026-10-05) عمود users.pwa_installed_at — أول لحظة شُغّل فيها الموقع
بوضع standalone (تثبيت PWA حقيقي على الشاشة الرئيسية)، عشان الأدمن يقدر
يشوف مين ثبّت التطبيق فعلياً بدل التخمين.

التشغيل:
  docker cp backend/migrate_add_pwa_installed.py moshapi_backend:/app/
  docker compose -f docker-compose.prod.yml exec backend python /app/migrate_add_pwa_installed.py
"""
import sys
sys.path.insert(0, "/app")
from app.database import engine
from sqlalchemy import text


def migrate():
    with engine.connect() as conn:
        try:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN pwa_installed_at TIMESTAMP WITH TIME ZONE"
            ))
            conn.commit()
            print("✅ Column users.pwa_installed_at added")
        except Exception as e:
            conn.rollback()
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print("ℹ️  Column users.pwa_installed_at already exists — skipping")
            else:
                print(f"❌ Error adding column: {e}")
                raise


if __name__ == "__main__":
    migrate()
