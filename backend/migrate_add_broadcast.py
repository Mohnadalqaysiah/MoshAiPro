"""
migrate_add_broadcast.py
Adds broadcast_sent column to signals table.
Run: docker exec moshapi_backend python /app/migrate_add_broadcast.py
"""
import sys
sys.path.insert(0, "/app")
from app.database import engine
from sqlalchemy import text

def migrate():
    with engine.connect() as conn:
        try:
            conn.execute(text(
                "ALTER TABLE signals ADD COLUMN broadcast_sent BOOLEAN NOT NULL DEFAULT FALSE"
            ))
            conn.commit()
            print("✅ Column broadcast_sent added successfully")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print("ℹ️  Column already exists — skipping")
            else:
                print(f"❌ Error: {e}")
                raise

if __name__ == "__main__":
    migrate()
