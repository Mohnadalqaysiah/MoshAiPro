"""
Admin Telegram Notifications
Sends instant alerts to @Mgaisi when new users register or payments are submitted.
"""
import requests
from loguru import logger
from app.config import get_settings


def _resolve_bot_token(settings) -> str:
    """Check SiteSettings DB for telegram_bot_token override, fall back to env var."""
    try:
        from app.database import SessionLocal
        from app.models.site_settings import SiteSettings
        db = SessionLocal()
        try:
            row = db.query(SiteSettings).filter(SiteSettings.key == "telegram_bot_token").first()
            if row and row.value and row.value.strip():
                return row.value.strip()
        finally:
            db.close()
    except Exception:
        pass
    return (settings.TELEGRAM_BOT_TOKEN or "").strip()


def get_bot_token() -> str:
    """Public helper: resolves the active Telegram bot token (DB override first, then env)."""
    return _resolve_bot_token(get_settings())


def notify_admin_telegram(message: str) -> None:
    """Send a Telegram message to the admin (ADMIN_TELEGRAM_ID). Runs in background."""
    settings = get_settings()
    admin_id = settings.ADMIN_TELEGRAM_ID.strip()
    bot_token = _resolve_bot_token(settings)

    if not admin_id or not bot_token:
        return  # Not configured — silently skip

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        resp = requests.post(url, json={
            "chat_id": admin_id,
            "text": message,
            "parse_mode": "HTML",
        }, timeout=8)
        if not resp.ok:
            logger.warning(f"Admin notify failed: {resp.text}")
    except Exception as e:
        logger.warning(f"Admin notify error: {e}")
