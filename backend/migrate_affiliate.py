"""
migrate_affiliate.py — إضافة نظام الأفلييت
شغّل داخل container:
  docker compose -f docker-compose.prod.yml exec backend python migrate_affiliate.py
"""
import secrets
import string

from app.database import engine, Base
from sqlalchemy import text, inspect

# import all models so Base.metadata is populated
from app.models import *            # noqa: F401 F403
from app.models.affiliate import Affiliate, AffiliateReferral  # noqa: F401


def _gen_code(conn) -> str:
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(secrets.choice(alphabet) for _ in range(8))
        exists = conn.execute(
            text("SELECT 1 FROM users WHERE affiliate_code = :c"), {"c": code}
        ).first()
        if not exists:
            return code


def run():
    insp = inspect(engine)

    # ── Step A: Add new columns to users ─────────────────────────────────────
    user_cols = {c["name"] for c in insp.get_columns("users")}
    new_cols = [
        ("affiliate_code",   "VARCHAR(8)"),
        ("referred_by_code", "VARCHAR(8)"),
    ]
    with engine.connect() as conn:
        for col, typ in new_cols:
            if col not in user_cols:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {typ}"))
                print(f"✅ Added column users.{col}")
            else:
                print(f"ℹ️  users.{col} already exists")

        # Unique index on affiliate_code
        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_affiliate_code ON users(affiliate_code) WHERE affiliate_code IS NOT NULL"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_users_referred_by_code ON users(referred_by_code) WHERE referred_by_code IS NOT NULL"
        ))

        # ── Step B: Backfill affiliate_code for existing users ────────────────
        rows = conn.execute(
            text("SELECT id FROM users WHERE affiliate_code IS NULL")
        ).fetchall()
        for row in rows:
            code = _gen_code(conn)
            conn.execute(
                text("UPDATE users SET affiliate_code = :c WHERE id = :id"),
                {"c": code, "id": row[0]}
            )
        if rows:
            print(f"✅ Backfilled affiliate_code for {len(rows)} users")

        conn.commit()

    # ── Step C: Create affiliates table ──────────────────────────────────────
    if not insp.has_table("affiliates"):
        Affiliate.__table__.create(engine)
        print("✅ affiliates table created")
    else:
        print("ℹ️  affiliates already exists")

    # ── Step D: Create affiliate_referrals table ──────────────────────────────
    if not insp.has_table("affiliate_referrals"):
        AffiliateReferral.__table__.create(engine)
        print("✅ affiliate_referrals table created")
    else:
        print("ℹ️  affiliate_referrals already exists")

    # ── Step E: Backfill affiliates rows for existing users ───────────────────
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO affiliates (user_id, code, referred_by_code, total_referrals, pending_balance_usd, paid_out_usd)
            SELECT u.id, u.affiliate_code, u.referred_by_code, 0, 0.0, 0.0
            FROM users u
            LEFT JOIN affiliates a ON a.user_id = u.id
            WHERE a.id IS NULL
              AND u.affiliate_code IS NOT NULL
        """))
        conn.commit()
        print("✅ Backfilled affiliates rows")

    print("\n🎉 Affiliate migration complete!")


if __name__ == "__main__":
    run()
