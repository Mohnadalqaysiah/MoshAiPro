"""
migrate_add_support_attachments.py
===================================
يضيف أعمدة المرفقات (صورة/ملف) لجدول support_chat_messages، ويلغي قيد
NOT NULL عن body (رسالة ممكن تكون مرفق فقط بدون نص).

التشغيل:
  docker cp migrate_add_support_attachments.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/migrate_add_support_attachments.py
"""
import sys
sys.path.insert(0, "/app")
from app.database import engine
from sqlalchemy import text


def migrate():
    with engine.connect() as conn:
        for stmt, label in [
            ("ALTER TABLE support_chat_messages ADD COLUMN attachment_url VARCHAR", "attachment_url"),
            ("ALTER TABLE support_chat_messages ADD COLUMN attachment_name VARCHAR", "attachment_name"),
            ("ALTER TABLE support_chat_messages ADD COLUMN attachment_type VARCHAR", "attachment_type"),
        ]:
            try:
                conn.execute(text(stmt))
                conn.commit()
                print(f"✅ Column {label} added")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    print(f"ℹ️  Column {label} already exists — skipping")
                else:
                    print(f"❌ Error adding {label}: {e}")
                    raise

        try:
            conn.execute(text("ALTER TABLE support_chat_messages ALTER COLUMN body DROP NOT NULL"))
            conn.commit()
            print("✅ body is now nullable (attachment-only messages allowed)")
        except Exception as e:
            print(f"❌ Error relaxing body NOT NULL: {e}")
            raise


if __name__ == "__main__":
    migrate()
