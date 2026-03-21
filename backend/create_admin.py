"""
سكريبت لإنشاء أول مدير للنظام
الاستخدام: python create_admin.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, init_db
from app.models.user import User, UserRole, PlanType
from app.services.auth_service import hash_password
from datetime import datetime, timezone

# ─── إعدادات المدير الأول ────────────────────────────────────────────────────
ADMIN_EMAIL    = "admin@moshaipro.com"
ADMIN_PASSWORD = "Admin@123456"
ADMIN_NAME     = "مدير النظام"
# ─────────────────────────────────────────────────────────────────────────────

def create_admin():
    init_db()
    db = SessionLocal()

    existing = db.query(User).filter(User.email == ADMIN_EMAIL).first()
    if existing:
        if existing.role != UserRole.ADMIN:
            existing.role = UserRole.ADMIN
            db.commit()
            print(f"✅ تم ترقية المستخدم {ADMIN_EMAIL} إلى مدير")
        else:
            print(f"ℹ️  المدير {ADMIN_EMAIL} موجود مسبقاً")
        return

    admin = User(
        email         = ADMIN_EMAIL,
        password_hash = hash_password(ADMIN_PASSWORD),
        full_name     = ADMIN_NAME,
        role          = UserRole.ADMIN,
        plan          = PlanType.MONTHLY,
        is_active     = True,
        trial_analyses_left = 9999,
        trial_chat_left     = 9999,
        subscription_ends_at = datetime(2099, 1, 1, tzinfo=timezone.utc),
    )
    db.add(admin)
    db.commit()
    print(f"✅ تم إنشاء المدير بنجاح!")
    print(f"   البريد: {ADMIN_EMAIL}")
    print(f"   كلمة المرور: {ADMIN_PASSWORD}")
    print(f"   ⚠️  غيّر كلمة المرور فوراً من لوحة الإدارة!")
    db.close()

if __name__ == "__main__":
    create_admin()
