"""
migrate_add_antiabuse.py
Adds registration_ip and is_verified columns to users table.
Run: docker exec moshapi_backend python /app/migrate_add_antiabuse.py
"""
import sys
sys.path.insert(0, "/app")
from app.database import engine
from sqlalchemy import text

def migrate():
    with engine.connect() as conn:
        try:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN registration_ip VARCHAR"
            ))
            conn.commit()
            print("✅ Column registration_ip added successfully")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print("ℹ️  Column registration_ip already exists — skipping")
            else:
                print(f"❌ Error: {e}")
                raise

        try:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN is_verified BOOLEAN NOT NULL DEFAULT FALSE"
            ))
            conn.commit()
            print("✅ Column is_verified added successfully")
            # Grandfather existing users — only NEW registrations after this
            # migration should be required to verify their email.
            conn.execute(text("UPDATE users SET is_verified = TRUE"))
            conn.commit()
            print("✅ Existing users grandfathered as verified")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print("ℹ️  Column is_verified already exists — skipping")
            else:
                print(f"❌ Error: {e}")
                raise

if __name__ == "__main__":
    migrate()
