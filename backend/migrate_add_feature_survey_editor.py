"""
migrate_add_feature_survey_editor.py
========================================
(2026-09-27) استطلاع "ساعدنا نطور المنصة لك" صار قابلاً للتعديل الكامل من
لوحة الأدمن (سؤال + خيارات) بدل نص ثابت بالكود. يضيف عمودين لجدولين
موجودين مسبقاً:
  - users.feature_survey_seen_id (Integer) — أي نسخة استطلاع رآها المستخدم.
  - feature_requests.survey_id (Integer)   — أي نسخة أُجيب عليها.
جدول feature_surveys نفسه جديد بالكامل — يُنشأ تلقائياً عبر create_all
عند إقلاع الـbackend التالي، لا يحتاج migration يدوي.

التشغيل:
  docker cp migrate_add_feature_survey_editor.py moshapi_backend:/app/
  docker compose -f docker-compose.prod.yml exec backend python /app/migrate_add_feature_survey_editor.py
"""
import sys
sys.path.insert(0, "/app")
from app.database import engine
from sqlalchemy import text


def migrate():
    with engine.connect() as conn:
        for stmt, label in [
            ("ALTER TABLE users ADD COLUMN feature_survey_seen_id INTEGER", "users.feature_survey_seen_id"),
            ("ALTER TABLE feature_requests ADD COLUMN survey_id INTEGER", "feature_requests.survey_id"),
        ]:
            try:
                conn.execute(text(stmt))
                conn.commit()
                print(f"✅ Column {label} added")
            except Exception as e:
                conn.rollback()
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    print(f"ℹ️  Column {label} already exists — skipping")
                else:
                    print(f"❌ Error adding {label}: {e}")
                    raise


if __name__ == "__main__":
    migrate()
