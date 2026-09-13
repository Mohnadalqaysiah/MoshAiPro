"""
migrate_add_feature_survey.py
================================
(2026-09-13) يضيف عمود feature_survey_dismissed (Boolean) لجدول users.

الغرض: تتبّع هل المستخدم شاهد بوب أب استطلاع "ساعدنا نطور المنصة لك"
(سواء أرسل إجابة أو ضغط تخطّي) — حتى لا يظهر له مرة ثانية بأي تسجيل
دخول لاحق. جدول feature_requests نفسه (سجل الإجابات) يُنشأ تلقائياً
عبر create_all عند إقلاع الـbackend التالي — لا يحتاج migration يدوي
لأنه جدول جديد بالكامل، بعكس عمود على جدول موجود مسبقاً.

التشغيل:
  docker cp migrate_add_feature_survey.py moshapi_backend:/app/
  docker compose -f docker-compose.prod.yml exec backend python /app/migrate_add_feature_survey.py
"""
import sys
sys.path.insert(0, "/app")
from app.database import engine
from sqlalchemy import text


def migrate():
    with engine.connect() as conn:
        try:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN feature_survey_dismissed BOOLEAN NOT NULL DEFAULT FALSE"
            ))
            conn.commit()
            print("✅ Column feature_survey_dismissed added")
        except Exception as e:
            conn.rollback()
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print("ℹ️  Column feature_survey_dismissed already exists — skipping")
            else:
                print(f"❌ Error adding column: {e}")
                raise


if __name__ == "__main__":
    migrate()
