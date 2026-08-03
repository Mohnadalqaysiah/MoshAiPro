"""
migrate_add_stripe.py
Adds provider and stripe_payment_intent columns to payments table.
Run: docker exec moshapi_backend python /app/migrate_add_stripe.py
"""
import sys
sys.path.insert(0, "/app")
from app.database import engine
from sqlalchemy import text

def migrate():
    with engine.connect() as conn:
        try:
            conn.execute(text(
                "ALTER TABLE payments ADD COLUMN provider VARCHAR NOT NULL DEFAULT 'usdt'"
            ))
            conn.commit()
            print("✅ Column provider added successfully")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print("ℹ️  Column provider already exists — skipping")
            else:
                print(f"❌ Error: {e}")
                raise

        try:
            conn.execute(text(
                "ALTER TABLE payments ADD COLUMN stripe_payment_intent VARCHAR"
            ))
            conn.commit()
            print("✅ Column stripe_payment_intent added successfully")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print("ℹ️  Column stripe_payment_intent already exists — skipping")
            else:
                print(f"❌ Error: {e}")
                raise

if __name__ == "__main__":
    migrate()
