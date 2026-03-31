"""
Migration: إضافة عمود result_broadcast_sent لجدول signals
يُمثّل هذا العمود أن نتيجة الإشارة (TP/SL) قد بُثّت لجميع المشتركين.
تشغيل:
    docker exec moshapi_backend python /app/migrate_add_result_broadcast.py
"""
import sys
from sqlalchemy import text
from app.database import engine

ADD_COL_SQL = """
ALTER TABLE signals
    ADD COLUMN IF NOT EXISTS result_broadcast_sent BOOLEAN NOT NULL DEFAULT FALSE;
"""

def run():
    with engine.connect() as conn:
        conn.execute(text(ADD_COL_SQL))
        conn.commit()
    print("✅ Migration complete: signals.result_broadcast_sent added")

if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"❌ Migration failed: {e}", file=sys.stderr)
        sys.exit(1)
