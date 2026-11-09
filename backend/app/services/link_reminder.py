"""
(2026-11-09) تذكير ربط تيليجرام — قمع الربط (diag_link_funnel.py، DECISIONS 09/11).

القياس: 95% ممن يربطون يربطون خلال ساعة من التسجيل، ولم يكن هناك أي تذكير لمن فاتته اللحظة.
هنا تذكير واحد فقط، بعد REMIND_AFTER_H من التسجيل، لمن لم يربط بعد:
  - إشعار المتصفح أولاً إن كان له اشتراك (يفتح شاشة الربط مباشرة)، وإلا إيميل برابط ربط بضغطة.
  - للجدد فقط (حتى REMIND_MAX_AGE_H): لا نرسل لقاعدة المستخدمين القديمة كلها عند النشر.
  - لا يُرسل لمن أوقف الإشعارات، أو لم يفعّل بريده (بريد غير مؤكَّد قد لا يكون له)، أو المعطَّل، أو الأدمن.
  - telegram_link_reminded_at يُوسم دائماً بعد المعالجة — مرة واحدة حتى لو فشل الإرسال.

نفس نمط checkout_reminder.py (asyncio task + قفل وحيد بين العاملين).
"""
import asyncio
import secrets
from datetime import datetime, timedelta, timezone

from loguru import logger

CHECK_INTERVAL_SEC = 30 * 60
REMIND_AFTER_H = 24
REMIND_MAX_AGE_H = 72
_LOCK_KEY = 90210011          # 90210001..90210010 مستخدمة


def due_users(db, now: datetime) -> list:
    from app.models.user import User, UserRole
    return (db.query(User)
            .filter(User.telegram_id.is_(None),
                    User.telegram_link_reminded_at.is_(None),
                    User.role != UserRole.ADMIN,
                    User.is_active.is_(True),
                    User.is_verified.is_(True),
                    User.created_at <= now - timedelta(hours=REMIND_AFTER_H),
                    User.created_at >= now - timedelta(hours=REMIND_MAX_AGE_H))
            .all())


def process(db, now: datetime, *, bot_username: str, send_email, send_push) -> dict:
    """يرجع {"push": n, "email": n, "skipped": n}. الدالتان تُمرَّران (تُستبدلان بالاختبار)."""
    from app.services.email_service import telegram_link_reminder_email_body
    out = {"push": 0, "email": 0, "skipped": 0}
    for u in due_users(db, now):
        u.telegram_link_reminded_at = now
        if u.notifications_enabled is False:
            out["skipped"] += 1
            continue
        en = (u.language or "ar") == "en"
        if send_push(db, u,
                     "One step left: link Telegram 📲" if en else "خطوة أخيرة: اربط تيليجرام 📲",
                     "So signals reach you the moment they're issued" if en else "لتصلك الإشارات لحظة صدورها",
                     url="/dashboard?link=telegram", tag="telegram-link"):
            out["push"] += 1
            continue
        if not u.email:
            out["skipped"] += 1
            continue
        if not u.telegram_link_token:
            u.telegram_link_token = secrets.token_urlsafe(16)
        link = f"https://t.me/{bot_username}?start={u.telegram_link_token}"
        send_email(u.email,
                   "One step left: link Telegram — Qaffel AI" if en else "خطوة أخيرة: اربط تيليجرام — Qaffel AI",
                   telegram_link_reminder_email_body(u.full_name or "", link, "en" if en else "ar"))
        out["email"] += 1
    db.commit()
    return out


async def link_reminder_checker():
    from app.api.auth import _get_bot_username
    from app.database import SessionLocal
    from app.services.email_service import send_email
    from app.services.web_push import send_push
    from app.services.worker_lock import try_acquire_singleton_lock

    lock_conn = try_acquire_singleton_lock(_LOCK_KEY, "Telegram link reminder")
    if lock_conn is None:
        return
    logger.info("🔒 Telegram link reminder: acquired singleton lock — running")
    while True:
        try:
            await asyncio.sleep(CHECK_INTERVAL_SEC)
            db = SessionLocal()
            try:
                res = process(db, datetime.now(timezone.utc), bot_username=_get_bot_username(db),
                              send_email=send_email, send_push=send_push)
                if res["push"] or res["email"]:
                    logger.info(f"📲 Telegram link reminder: {res}")
            finally:
                db.close()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Telegram link reminder error: {e}")
    lock_conn.close()
