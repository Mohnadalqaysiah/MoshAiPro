"""
migrate_add_telegram_linked_at.py
====================================
(2026-09-16) يضيف عمود telegram_linked_at (DateTime) لجدول users.

الغرض: قياس أثر أي تحسين على ربط تيليجرام. المتاح قبله كان "مرتبط
الآن أم لا" فقط، ومقارنة نسب الربط بين فترات تسجيل مختلفة منحازة
بنيوياً (من سجّل أمس أمامه يوم واحد ليربط، ومن سجّل قبل شهر أمامه 30
يوماً) — فتُظهر انحداراً وهمياً حتى لو كانت النسبة ثابتة تماماً.
بوجود العمود يصير القياس العادل ممكناً: "نسبة من ربط خلال أول 48 ساعة
من التسجيل" مقارنةً بين فوج ما قبل التحسين وفوج ما بعده.

⚠️ الصفوف القديمة تبقى NULL — لا يمكن استنتاج وقت ربط لم يُسجَّل
إطلاقاً، وأي تخمين (مثل استخدام created_at) سيفسد المقارنة نفسها التي
أُضيف العمود من أجلها. القياس العادل يبدأ من تاريخ هذا الترحيل.

التشغيل:
  docker cp migrate_add_telegram_linked_at.py moshapi_backend:/app/
  docker compose -f docker-compose.prod.yml exec backend python /app/migrate_add_telegram_linked_at.py
"""
import sys
sys.path.insert(0, "/app")
from app.database import engine
from sqlalchemy import text


def migrate():
    with engine.connect() as conn:
        try:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN telegram_linked_at TIMESTAMPTZ"
            ))
            conn.commit()
            print("✅ Column telegram_linked_at added")
        except Exception as e:
            conn.rollback()
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print("ℹ️  Column telegram_linked_at already exists — skipping")
            else:
                print(f"❌ Error adding column: {e}")
                raise

        n = conn.execute(text(
            "SELECT COUNT(*) FROM users WHERE telegram_id IS NOT NULL"
        )).scalar()
        print(f"ℹ️  {n} مستخدماً مرتبطاً حالياً ستبقى قيمتهم NULL عمداً "
              f"(وقت ربطهم لم يُسجَّل، وتخمينه يفسد المقارنة).")


if __name__ == "__main__":
    migrate()
