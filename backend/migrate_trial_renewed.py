"""Migration: add trial_renewed_at column to users"""
import sys
sys.path.insert(0, "/app")
from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    try:
        conn.execute(text(
            "ALTER TABLE users ADD COLUMN trial_renewed_at TIMESTAMP WITH TIME ZONE"
        ))
        conn.commit()
        print("✅ Added trial_renewed_at to users")
    except Exception as e:
        if "already exists" in str(e).lower():
            print("⚠️  Column already exists — skipping")
        else:
            print(f"❌ Error: {e}")
            sys.exit(1)
