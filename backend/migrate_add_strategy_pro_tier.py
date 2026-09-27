"""
migrate_add_strategy_pro_tier.py
========================================
(2026-09-27) باني الاستراتيجيات صار مسيَّراً منفصلاً عن الأسبوعي/الشهري
العاديين (قرار صاحب المنتج، راجع DECISIONS.md). يضيف 3 أعمدة لجدول users
الموجود مسبقاً، ثم يُقفل الوصول الكامل الحالي (grandfather) لكل مشترك
أسبوعي/شهري فعلي وقت التشغيل — هذا الاستثناء لا يتكرر مع أي مشترك جديد
بعد هذه اللحظة.

⚠️ شغّله مرة واحدة فقط عند إطلاق الميزة. تشغيله لاحقاً بلا تعديل سيمنح
grandfathering لمشتركين جدد أيضاً — ليس الهدف.

التشغيل:
  docker cp migrate_add_strategy_pro_tier.py moshapi_backend:/app/
  docker compose -f docker-compose.prod.yml exec backend python /app/migrate_add_strategy_pro_tier.py
"""
import sys
sys.path.insert(0, "/app")
from app.database import engine
from sqlalchemy import text


def migrate():
    with engine.connect() as conn:
        for stmt, label in [
            ("ALTER TABLE users ADD COLUMN strategy_builder_grandfathered BOOLEAN NOT NULL DEFAULT FALSE", "users.strategy_builder_grandfathered"),
            ("ALTER TABLE users ADD COLUMN strategy_pro_until TIMESTAMP WITH TIME ZONE", "users.strategy_pro_until"),
            ("ALTER TABLE users ADD COLUMN strategy_free_alerts_left INTEGER NOT NULL DEFAULT 3", "users.strategy_free_alerts_left"),
            ("ALTER TABLE users ADD COLUMN is_yearly_subscriber BOOLEAN NOT NULL DEFAULT FALSE", "users.is_yearly_subscriber"),
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

        try:
            result = conn.execute(text(
                "UPDATE users SET strategy_builder_grandfathered = TRUE "
                "WHERE plan IN ('weekly', 'monthly') AND strategy_builder_grandfathered = FALSE"
            ))
            conn.commit()
            print(f"✅ Grandfathered {result.rowcount} existing weekly/monthly subscribers")
        except Exception as e:
            conn.rollback()
            print(f"❌ Error grandfathering existing subscribers: {e}")
            raise

        # المشترك السنوي الحالي فعلياً (آخر دفعة مقبولة له plan='yearly'،
        # واشتراكه لسا سارٍ) — يُعلَّم is_yearly_subscriber بأثر رجعي.
        try:
            result = conn.execute(text("""
                UPDATE users u SET is_yearly_subscriber = TRUE
                WHERE u.is_yearly_subscriber = FALSE
                  AND u.subscription_ends_at > NOW()
                  AND (
                      SELECT p.plan FROM payments p
                      WHERE p.user_id = u.id AND p.status = 'approved'
                      ORDER BY p.created_at DESC LIMIT 1
                  ) = 'yearly'
            """))
            conn.commit()
            print(f"✅ Marked {result.rowcount} existing users as yearly subscribers")
        except Exception as e:
            conn.rollback()
            print(f"❌ Error backfilling is_yearly_subscriber: {e}")
            raise


if __name__ == "__main__":
    migrate()
