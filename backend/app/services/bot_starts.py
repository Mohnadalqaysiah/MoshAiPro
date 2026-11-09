"""
(2026-11-09) تسجيل من ضغط Start في البوت بلا رابط ربط — models/bot_start.py، ويقرؤه diag_link_funnel.py.
"""
from datetime import datetime, timezone

from app.models.bot_start import BotStart
from app.models.user import User


def record_start(db, telegram_id: str, lang: str = "") -> dict:
    """يسجّل الضغطة (صف لكل حساب تيليجرام) ويرجع هل هذا الحساب مربوط بحساب بالمنصة."""
    tid = str(telegram_id or "").strip()
    if not tid:
        return {"linked": False}
    linked = db.query(User.id).filter(User.telegram_id == tid).first() is not None
    now = datetime.now(timezone.utc)
    row = db.query(BotStart).filter(BotStart.telegram_id == tid).first()
    if row is None:
        db.add(BotStart(telegram_id=tid, first_at=now, last_at=now, starts=1,
                        had_account=linked, lang=(lang or "")[:8] or None))
    else:
        row.last_at = now
        row.starts = (row.starts or 0) + 1
    db.commit()
    return {"linked": linked}
