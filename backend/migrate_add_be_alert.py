"""
Migration: إضافة عمود be_alert_sent لجدول signals (2026-10-11)
يُمثّل أن تنبيه "حرّك الستوب للدخول" عند بلوغ +1R أُرسل لهذا القرار.
تشغيل:
    docker exec moshapi_backend python /app/migrate_add_be_alert.py
"""
import sys
from sqlalchemy import text
from app.database import engine

ADD_COL_SQL = """
ALTER TABLE signals
    ADD COLUMN IF NOT EXISTS be_alert_sent BOOLEAN DEFAULT FALSE;
"""


def run():
    with engine.connect() as conn:
        conn.execute(text(ADD_COL_SQL))
        conn.commit()
    print("✅ Migration complete: signals.be_alert_sent added")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"❌ Migration failed: {e}", file=sys.stderr)
        sys.exit(1)
