"""
migrate_add_coupons_yearly.py
================================
هجرة يدوية لما لا ينشئه Base.metadata.create_all() تلقائياً.

ما يحتاج تدخّلاً وما لا يحتاج:
  • جدولا coupons / coupon_redemptions → جديدان، ينشئهما create_all عند
    إقلاع الخادم. لا شيء هنا.
  • paymentplan → نوع enum قائم بقاعدة البيانات، وإضافة قيمة له تحتاج
    ALTER TYPE صراحةً. لولاها يفشل أي دفع سنوي بـInvalidTextRepresentation.
  • payments.coupon_code / discount_percent → أعمدة على جدول قائم،
    وcreate_all لا يضيف أعمدة لجداول موجودة.

⚠️ ALTER TYPE ... ADD VALUE لا يُنفَّذ داخل كتلة معاملات على PostgreSQL،
لذا نستخدم AUTOCOMMIT. والسكربت idempotent: إعادة تشغيله لا تضر.

التشغيل:
  docker cp migrate_add_coupons_yearly.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/migrate_add_coupons_yearly.py
"""
import sys
sys.path.insert(0, "/app")

from sqlalchemy import text
from app.database import engine


def enum_values(conn, type_name: str) -> list:
    rows = conn.execute(text(
        "SELECT e.enumlabel FROM pg_enum e "
        "JOIN pg_type t ON t.oid = e.enumtypid WHERE t.typname = :tn"
    ), {"tn": type_name}).fetchall()
    return [r[0] for r in rows]


def main():
    print("=" * 74)
    print("هجرة: الباقة السنوية + كوبونات الخصم")
    print("=" * 74)

    # ── 1) قيمة YEARLY بنوع paymentplan ────────────────────────────────
    # SQLAlchemy يخزّن أسماء أعضاء enum لا قيمها، فالقيمة المطلوبة
    # 'YEARLY' بحروف كبيرة. نقرأ الموجود أولاً بدل الافتراض.
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        vals = enum_values(conn, "paymentplan")
        if not vals:
            print("  ⚠️ لم يُعثر على النوع paymentplan — تخطٍّ "
                  "(قاعدة جديدة سينشئها create_all كاملة).")
        elif "YEARLY" in vals:
            print(f"  ✅ paymentplan يحوي YEARLY مسبقاً {vals}")
        else:
            conn.execute(text("ALTER TYPE paymentplan ADD VALUE IF NOT EXISTS 'YEARLY'"))
            print(f"  ➕ أُضيفت YEARLY إلى paymentplan (كانت {vals})")

    # ── 2) عمودا الكوبون على جدول payments ─────────────────────────────
    with engine.begin() as conn:
        for col, ddl in (
            ("coupon_code",      "ALTER TABLE payments ADD COLUMN IF NOT EXISTS coupon_code VARCHAR"),
            ("discount_percent", "ALTER TABLE payments ADD COLUMN IF NOT EXISTS discount_percent DOUBLE PRECISION"),
        ):
            exists = conn.execute(text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'payments' AND column_name = :c"
            ), {"c": col}).fetchone()
            if exists:
                print(f"  ✅ payments.{col} موجود مسبقاً")
            else:
                conn.execute(text(ddl))
                print(f"  ➕ أُضيف payments.{col}")

    # ── 3) تأكيد وجود جدولي الكوبونات ──────────────────────────────────
    with engine.connect() as conn:
        for tbl in ("coupons", "coupon_redemptions"):
            found = conn.execute(text(
                "SELECT 1 FROM information_schema.tables WHERE table_name = :t"
            ), {"t": tbl}).fetchone()
            print(f"  {'✅' if found else 'ℹ️ '} جدول {tbl}: "
                  f"{'موجود' if found else 'سيُنشأ عند إقلاع الخادم القادم'}")

    print("\n✅ انتهت الهجرة.")
    print("   أعد تشغيل الـbackend ليُنشئ create_all جدولي الكوبونات إن لزم.")


if __name__ == "__main__":
    main()
