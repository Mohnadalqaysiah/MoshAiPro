"""
Qaffel AI — Migration v4
Adds TwelveData toggle + user limits to site_settings
"""
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://moshuser:moshpass@localhost:5432/moshaiprodb"
)

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    conn.execute(text("""
        INSERT INTO site_settings (key, value, description)
        VALUES
            ('twelvedata_api_key',    '',     'مفتاح TwelveData API (اختياري)'),
            ('twelvedata_enabled',    'false', 'تفعيل TwelveData كمصدر احتياطي (true/false)'),
            ('trial_chat_limit',      '20',   'عدد محادثات الحساب التجريبي'),
            ('trial_analysis_limit',  '10',   'عدد التحليلات للحساب التجريبي'),
            ('weekly_chat_limit',     '200',  'عدد محادثات الباقة الأسبوعية'),
            ('weekly_analysis_limit', '100',  'عدد التحليلات للباقة الأسبوعية'),
            ('monthly_chat_limit',    '1000', 'عدد محادثات الباقة الشهرية'),
            ('monthly_analysis_limit','500',  'عدد التحليلات للباقة الشهرية')
        ON CONFLICT (key) DO NOTHING
    """))

    conn.commit()
    print("✅ migrate_v4: TwelveData + limits settings added")
