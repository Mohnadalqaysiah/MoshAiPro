"""
migrate_add_support_notify_cooldown.py
=======================================
يضيف عمود last_admin_notify_at لجدول support_chat_threads — يُستخدم
لمنع إرسال تنبيه تلغرام للأدمن عن كل رسالة دعم (كان مزعجاً)، فيصير
تنبيه واحد كحد أقصى كل N دقيقة لكل محادثة بدل تنبيه لكل رسالة.

التشغيل:
  docker cp migrate_add_support_notify_cooldown.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/migrate_add_support_notify_cooldown.py
"""
import sys
sys.path.insert(0, "/app")
from app.database import engine
from sqlalchemy import text


def migrate():
    with engine.connect() as conn:
        try:
            conn.execute(text(
                "ALTER TABLE support_chat_threads ADD COLUMN last_admin_notify_at TIMESTAMPTZ"
            ))
            conn.commit()
            print("✅ Column last_admin_notify_at added")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print("ℹ️  Column already exists — skipping")
            else:
                print(f"❌ Error: {e}")
                raise


if __name__ == "__main__":
    migrate()
