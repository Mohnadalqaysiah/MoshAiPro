"""
(2026-11-11، المالك: "بدي الناس تشارك ارباحها او نتائجها صور لقطات شاشة… وتوصلني انا بشكل مباشر… ممكن من البوت")

المسار: زر "📸 شارك نتيجتك" بالبوت ← صورة (أو ملف صورة) مع وصف اختياري ← اختيار النشر (باسمي / بدون اسمي / للفريق فقط)
← POST /api/v1/bot/result-share ← صف ResultShare + إرسال الصورة للمالك (ADMIN_TELEGRAM_ID) بنفس البوت، ومعها هوية المرسل واختياره.
النشر في القناة يبقى بيد المالك ويحترم اختيار صاحبها — لا نشر آلي. حد يومي لكل حساب تيليجرام ضد الإغراق.
"""
import html
from datetime import datetime, timedelta, timezone

import requests
from loguru import logger

from app.models.result_share import ResultShare
from app.models.user import User

CONSENTS = {"name": "تُنشر باسمه", "anon": "تُنشر بدون اسمه", "private": "للفريق فقط — لا تُنشر"}
KINDS = ("photo", "document")
DAILY_MAX = 10
CAPTION_MAX = 500


def record_share(db, data: dict) -> dict:
    tid = str(data.get("telegram_id") or "").strip()
    fid = str(data.get("file_id") or "").strip()
    kind = data.get("file_kind")
    consent = data.get("consent")
    if not tid or not fid or kind not in KINDS:
        return {"ok": False, "error": "أرسل صورة فقط"}
    if consent not in CONSENTS:
        return {"ok": False, "error": "اختر طريقة النشر"}
    since = datetime.now(timezone.utc) - timedelta(days=1)
    if db.query(ResultShare).filter(ResultShare.telegram_id == tid, ResultShare.created_at >= since).count() >= DAILY_MAX:
        return {"ok": False, "error": f"وصلت للحد اليومي ({DAILY_MAX} صور) — حاول غداً"}
    user = db.query(User).filter(User.telegram_id == tid).first()
    row = ResultShare(telegram_id=tid, user_id=user.id if user else None,
                      tg_username=(data.get("username") or "")[:64] or None,
                      tg_name=(data.get("name") or "")[:128] or None,
                      file_kind=kind, file_id=fid,
                      caption=(data.get("caption") or "").strip()[:CAPTION_MAX] or None,
                      consent=consent, created_at=datetime.now(timezone.utc))
    db.add(row)
    db.commit()
    return {"ok": True, "id": row.id}


def owner_caption(row: ResultShare, user) -> str:
    who = html.escape(row.tg_name or "بدون اسم")
    if row.tg_username:
        who += f" (@{html.escape(row.tg_username)})"
    if user:
        plan = getattr(user.plan, "value", user.plan) or ""
        acct = f"{html.escape(user.email or '')} · {html.escape(str(plan))}"
    else:
        acct = "غير مربوط بحساب"
    out = (f"📸 <b>نتيجة جديدة من مستخدم</b>\n👤 {who}\n🔗 {acct}\n"
           f"📣 {CONSENTS.get(row.consent, row.consent)}")
    if row.caption:
        out += f"\n\n📝 {html.escape(row.caption)}"
    return out[:1000]                                     # حد تعليق الصورة بتيليجرام 1024


def send_to_owner(share_id: int) -> None:
    from app.config import get_settings
    from app.database import SessionLocal
    from app.services.admin_notify import get_bot_token
    db = SessionLocal()
    try:
        row = db.query(ResultShare).filter(ResultShare.id == share_id).first()
        if not row:
            return
        admin_id = (get_settings().ADMIN_TELEGRAM_ID or "").strip()
        token = get_bot_token()
        if not admin_id or not token:
            logger.warning("result-share: ADMIN_TELEGRAM_ID أو توكن البوت غير مضبوط — لم تُرسل للمالك")
            return
        user = db.query(User).filter(User.id == row.user_id).first() if row.user_id else None
        method, field = ("sendPhoto", "photo") if row.file_kind == "photo" else ("sendDocument", "document")
        try:
            resp = requests.post(f"https://api.telegram.org/bot{token}/{method}",
                                 json={"chat_id": admin_id, field: row.file_id,
                                       "caption": owner_caption(row, user), "parse_mode": "HTML"}, timeout=20)
            if resp.ok:
                row.sent_to_owner_at = datetime.now(timezone.utc)
                db.commit()
            else:
                logger.warning(f"result-share → owner failed: {resp.text[:200]}")
        except Exception as e:
            logger.warning(f"result-share → owner error: {e}")
    finally:
        db.close()
