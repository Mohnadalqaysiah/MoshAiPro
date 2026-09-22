"""
migrate_add_google_auth.py
======================================
يجهّز جدول users لتسجيل الدخول بحساب Google:
  1. يجعل password_hash قابلاً لـNULL — حسابات Google ما عندها كلمة سر
     إطلاقاً، التحقق يصير عبر Firebase ID token لا verify_password.
  2. يضيف عمود auth_provider ("password" | "google") — يميّز مصدر الحساب
     لأغراض العرض ومنع محاولة دخول بكلمة سر على حساب Google بلا واحدة.

كل المستخدمين الحاليين قبل الهجرة auth_provider='password' (لهم كلمة
سر أصلاً). idempotent: إعادة التشغيل لا تضر.

التشغيل:
  docker cp migrate_add_google_auth.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/migrate_add_google_auth.py
"""
import sys
sys.path.insert(0, "/app")

from sqlalchemy import text
from app.database import engine

TABLE = "users"


def main():
    print("=" * 70)
    print(f"هجرة: {TABLE} — دعم تسجيل الدخول بحساب Google")
    print("=" * 70)

    with engine.begin() as conn:
        tbl = conn.execute(text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = :t"
        ), {"t": TABLE}).fetchone()
        if not tbl:
            print(f"  ❌ جدول {TABLE} غير موجود — تحقق من DATABASE_URL.")
            return

        # 1) password_hash → NULLABLE
        col = conn.execute(text(
            "SELECT is_nullable FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = 'password_hash'"
        ), {"t": TABLE}).fetchone()
        if col and col[0] == "YES":
            print("  ✅ password_hash قابل لـNULL مسبقاً — لا تغيير.")
        else:
            conn.execute(text(f"ALTER TABLE {TABLE} ALTER COLUMN password_hash DROP NOT NULL"))
            print("  ➕ password_hash صار قابلاً لـNULL.")

        # 2) auth_provider column
        exists = conn.execute(text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = 'auth_provider'"
        ), {"t": TABLE}).fetchone()
        if exists:
            print("  ✅ auth_provider موجود مسبقاً — لا تغيير.")
        else:
            conn.execute(text(
                f"ALTER TABLE {TABLE} ADD COLUMN IF NOT EXISTS auth_provider "
                f"VARCHAR NOT NULL DEFAULT 'password'"
            ))
            print("  ➕ أُضيف auth_provider (الافتراضي 'password' لكل الموجودين).")

        n = conn.execute(text(f"SELECT COUNT(*) FROM {TABLE}")).scalar()
        print(f"\n  مستخدمون موجودون: {n} (كلهم auth_provider='password')")

    print("\n✅ انتهت الهجرة. أعد تشغيل الـbackend.")


if __name__ == "__main__":
    main()
