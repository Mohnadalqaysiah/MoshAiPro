"""
migrate_add_signal_notif_masking.py
Adds signal_notif_seen_today / signal_notif_seen_date columns to users table —
tracks daily count of full (unmasked) Telegram signal broadcasts per user, so
trial/expired users still get notified when a masked signal shows up (see
bot.py::bot_active_subscribers and telegram-bot/bot.py::broadcast_new_signals).
Run: docker exec moshapi_backend python /app/migrate_add_signal_notif_masking.py
"""
import sys
sys.path.insert(0, "/app")
from app.database import engine
from sqlalchemy import text


def _add_column(conn, ddl: str, label: str):
    try:
        conn.execute(text(ddl))
        conn.commit()
        print(f"✅ {label} added successfully")
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            print(f"ℹ️  {label} already exists — skipping")
        else:
            print(f"❌ Error adding {label}: {e}")
            raise


def migrate():
    with engine.connect() as conn:
        _add_column(
            conn,
            "ALTER TABLE users ADD COLUMN signal_notif_seen_today INTEGER NOT NULL DEFAULT 0",
            "signal_notif_seen_today",
        )
        _add_column(
            conn,
            "ALTER TABLE users ADD COLUMN signal_notif_seen_date TIMESTAMPTZ",
            "signal_notif_seen_date",
        )


if __name__ == "__main__":
    migrate()
