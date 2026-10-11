"""
Migration: أعمدة التحدّي اليومي في game_progress (2026-10-11)
جدول game_progress أُنشئ بـcreate_all، و create_all لا يضيف أعمدة لجدول قائم.
تشغيل:
    docker exec moshapi_backend python /app/migrate_add_daily_challenge.py
"""
import sys
from sqlalchemy import text
from app.database import engine

SQL = [
    "ALTER TABLE game_progress ADD COLUMN IF NOT EXISTS daily_last VARCHAR",
    "ALTER TABLE game_progress ADD COLUMN IF NOT EXISTS daily_streak INTEGER DEFAULT 0",
]


def run():
    with engine.connect() as conn:
        exists = conn.execute(text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'game_progress'"
        )).first()
        if not exists:
            print("ℹ️  جدول game_progress غير موجود — سيُنشئه create_all كاملاً عند تشغيل الـbackend")
            return
        for s in SQL:
            conn.execute(text(s))
        conn.commit()
    print("✅ Migration complete: game_progress.daily_last / daily_streak added")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"❌ Migration failed: {e}", file=sys.stderr)
        sys.exit(1)
