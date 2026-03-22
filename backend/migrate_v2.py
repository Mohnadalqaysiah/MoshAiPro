"""
Migration v2: إضافة حقول account_balance و risk_percent للمستخدمين
شغّل هذا مرة واحدة على السيرفر بعد الـ deploy
"""
import os
import sys

# أضف المسار
sys.path.insert(0, "/app")

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://moshuser:moshpass@postgres:5432/moshaiprodb")

engine = create_engine(DATABASE_URL)

migrations = [
    """
    ALTER TABLE users
    ADD COLUMN IF NOT EXISTS account_balance FLOAT DEFAULT 10000.0;
    """,
    """
    ALTER TABLE users
    ADD COLUMN IF NOT EXISTS risk_percent FLOAT DEFAULT 1.5;
    """,
]

with engine.connect() as conn:
    for sql in migrations:
        try:
            conn.execute(text(sql))
            print(f"✅ Migration applied: {sql.strip()[:60]}...")
        except Exception as e:
            print(f"⚠️  Skipped (already exists?): {e}")
    conn.commit()

print("\n✅ Migration v2 complete!")
