"""
من حظر البوت (2026-10-19، قرار المالك)
=====================================
قياس 17-19/10: 147 مستخدماً حظروا البوت ← 5414 محاولة إرسال فاشلة في يومين (~134 لكل إشارة)، وكل محاولة تأخذ رحلة
شبكة + 0.05 ث، فتتأخر الإشارة على من ترتيبهم بعدهم. لا عطل تقني — تيليجرام يرد "Forbidden: bot was blocked by the user".

القاعدة:
- رد "محظور/محذوف/غير موجود" ← `users.telegram_blocked_at = الآن` ويُستبعد من كل قوائم الإرسال الجماعي.
- يرجع تلقائياً: (1) أي تفاعل له مع البوت (/start أو زر أو رسالة) ← `/bot/telegram-seen`، (2) أي إرسال ناجح له.
- محاولة احتياطية كل RETRY_DAYS: من فكّ الحظر دون أن يكتب للبوت يستلم أول إرسال بعد أسبوع من آخر فشل؛
  إن فشل ثانية يتجدد التاريخ فينتظر أسبوعاً آخر.
- الرسائل الموجّهة لمستخدمين محددين من اللوحة لا تُستبعد (الأدمن اختارهم بالاسم).
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.user import User

RETRY_DAYS = 7
_MARKERS = ("bot was blocked", "user is deactivated", "chat not found")


def is_unreachable(error) -> bool:
    e = (error or "").lower()
    return any(m in e for m in _MARKERS)


def reachable(now: datetime = None):
    """شرط SQLAlchemy يُضاف لاستعلامات مستلمي الإرسال الجماعي."""
    now = now or datetime.now(timezone.utc)
    return or_(User.telegram_blocked_at.is_(None), User.telegram_blocked_at < now - timedelta(days=RETRY_DAYS))


def should_skip(user, now: datetime = None) -> bool:
    """نفس `reachable` لقائمة مستخدمين محمّلة مسبقاً."""
    b = getattr(user, "telegram_blocked_at", None)
    if not b:
        return False
    now = now or datetime.now(timezone.utc)
    if b.tzinfo is None:
        b = b.replace(tzinfo=timezone.utc)
    return b >= now - timedelta(days=RETRY_DAYS)


def apply_results(db: Session, results) -> dict:
    """results: [(telegram_id, ok, error)]. يعلّم المحظور ويمسح علامة من وصله إرسال. لا يُنفّذ commit."""
    now = datetime.now(timezone.utc)
    blocked = {str(t) for t, ok, err in results if t and not ok and is_unreachable(err)}
    reached = {str(t) for t, ok, _ in results if t and ok}
    if blocked:
        db.query(User).filter(User.telegram_id.in_(blocked)).update(
            {User.telegram_blocked_at: now}, synchronize_session=False)
    if reached:
        db.query(User).filter(User.telegram_id.in_(reached), User.telegram_blocked_at.isnot(None)).update(
            {User.telegram_blocked_at: None}, synchronize_session=False)
    return {"blocked": len(blocked), "reached": len(reached)}


def mark_seen(db: Session, telegram_id: str) -> bool:
    n = db.query(User).filter(User.telegram_id == str(telegram_id), User.telegram_blocked_at.isnot(None)).update(
        {User.telegram_blocked_at: None}, synchronize_session=False)
    db.commit()
    return bool(n)
