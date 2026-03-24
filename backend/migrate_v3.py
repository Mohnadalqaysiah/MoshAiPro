"""
Qaffel AI — Migration v3
Creates site_settings table and seeds default values
"""
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://moshuser:moshpass@localhost:5432/moshaiprodb"
)

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Create site_settings table
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS site_settings (
            id          SERIAL PRIMARY KEY,
            key         VARCHAR UNIQUE NOT NULL,
            value       TEXT,
            description VARCHAR,
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))

    # Seed default wallet address
    conn.execute(text("""
        INSERT INTO site_settings (key, value, description)
        VALUES
            ('usdt_wallet', 'TVh8P92EEjr732frVRpxg1iE4GsfZpLM6E', 'عنوان محفظة USDT TRC20'),
            ('telegram_bot_username', 'Qaffelbot', 'اسم بوت تيليجرام بدون @')
        ON CONFLICT (key) DO NOTHING
    """))

    conn.commit()
    print("✅ migrate_v3: site_settings table created and seeded")
