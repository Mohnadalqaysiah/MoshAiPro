"""
Admin Telegram Notifications
Sends instant alerts to @Mgaisi when new users register or payments are submitted.
"""
import requests
from loguru import logger
from app.config import get_settings


def notify_admin_telegram(message: str) -> None:
    """Send a Telegram message to the admin (ADMIN_TELEGRAM_ID). Runs in background."""
    settings = get_settings()
    admin_id = settings.ADMIN_TELEGRAM_ID.strip()
    bot_token = settings.TELEGRAM_BOT_TOKEN.strip()

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
