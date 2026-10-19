"""
الحصة اليومية المجانية للإشارات الكاملة — مصدر واحد للموقع وتيليجرام (2026-10-19، قرار المالك "وحّد").

القاعدة: مستخدم بلا وصول كامل (تجربة نشطة أو منتهية) يفتح حتى `trial_signal_daily_limit` (افتراضي 3، 0 = بلا حد)
**قراراً مختلفاً** كل يوم UTC. أول ما يراه بأي قناة يُفتح ويُسجَّل؛ المسجَّل يبقى مفتوحاً بالقناتين حتى نهاية اليوم ولا
يُحسب مرتين. الوصول الكامل (أدمن/أسبوعي/شهري) لا يمر من هنا.
"""
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.signal_unlock import SignalUnlock
from app.models.site_settings import SiteSettings
from app.services.decision_grouping import decision_key


def daily_limit(db: Session) -> int:
    row = db.query(SiteSettings).filter(SiteSettings.key == "trial_signal_daily_limit").first()
    try:
        return int(row.value) if row and row.value else 3
    except Exception:
        return 3


def key_of(sig) -> str:
    m, tf, st, e = decision_key(sig.market, sig.timeframe, sig.signal_type, sig.entry_price)
    return f"{m}|{tf}|{st}|{e}"


def _today():
    return datetime.now(timezone.utc).date()


def unlocked_today(db: Session, user_id: int) -> set:
    rows = db.query(SignalUnlock.decision_key).filter(
        SignalUnlock.user_id == user_id, SignalUnlock.day == _today()).all()
    return {r[0] for r in rows}


def try_unlock(db: Session, user_id: int, sig, channel: str, limit: int = None, opened: set = None) -> bool:
    """يفتح القرار للمستخدم إن كان مفتوحاً اليوم أصلاً أو بقي من الحصة. `opened` (اختياري) = unlocked_today مُسبقاً
    ويُحدَّث هنا، لتجنّب استعلام لكل إشارة بقائمة طويلة."""
    limit = daily_limit(db) if limit is None else limit
    if limit <= 0:
        return True
    k = key_of(sig)
    if opened is None:
        opened = unlocked_today(db, user_id)
    if k in opened:
        return True
    if len(opened) >= limit:
        return False
    db.add(SignalUnlock(user_id=user_id, decision_key=k, day=_today(), channel=channel,
                        signal_id=getattr(sig, "id", None)))
    try:
        db.commit()
    except IntegrityError:          # طلبان متزامنان لنفس القرار — فتحه الآخر، والنتيجة واحدة
        db.rollback()
    opened.add(k)
    return True
