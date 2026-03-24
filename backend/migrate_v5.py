"""
migrate_v5.py — إضافة analysis_logs + أعمدة تفضيلات المستخدم
شغّل داخل container:
  docker compose -f docker-compose.prod.yml exec backend python migrate_v5.py
"""
from app.database import engine, Base
from sqlalchemy import text, inspect

# import all models so Base.metadata is populated
from app.models import *            # noqa: F401 F403
from app.models.analysis_log import AnalysisLog  # noqa: F401

def run():
    insp = inspect(engine)

    # ── جدول analysis_logs ────────────────────────────────────────────────────
    if not insp.has_table("analysis_logs"):
        AnalysisLog.__table__.create(engine)
        print("✅ analysis_logs table created")
    else:
        print("ℹ️  analysis_logs already exists")

    # ── أعمدة جديدة في users ──────────────────────────────────────────────────
    user_cols = {c["name"] for c in insp.get_columns("users")}
    new_cols = [
        ("notify_watchlist",      "JSONB DEFAULT '[]'::jsonb"),
        ("notify_timeframe",      "VARCHAR DEFAULT '1h'"),
        ("notify_min_confidence", "INTEGER DEFAULT 65"),
    ]
    with engine.connect() as conn:
        for col_name, col_def in new_cols:
            if col_name not in user_cols:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}"))
                conn.commit()
                print(f"✅ users.{col_name} added")
            else:
                print(f"ℹ️  users.{col_name} already exists")

    print("🎉 migrate_v5 done!")

if __name__ == "__main__":
    run()
