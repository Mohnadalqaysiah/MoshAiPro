"""
الحصة اليومية المجانية للإشارات الكاملة — مصدر واحد للموقع وتيليجرام (2026-10-19، قرار المالك "وحّد").

القاعدة: مستخدم بلا وصول كامل (تجربة نشطة أو منتهية) يفتح حتى `trial_signal_daily_limit` (افتراضي 3، 0 = بلا حد)
**قراراً مختلفاً** كل يوم UTC. أول ما يراه بأي قناة يُفتح ويُسجَّل؛ المسجَّل يبقى مفتوحاً بالقناتين حتى نهاية اليوم ولا
يُحسب مرتين. الوصول الكامل (أدمن/أسبوعي/شهري) لا يمر من هنا.

(2026-10-19، بعد النشر) **قفل لكل مستخدم:** الداشبورد يطلب /signals/latest من 4 مكوّنات بنفس اللحظة (القائمة، الشريط،
الخريطة، أفضل فرصة) — كل طلب قرأ "لا شيء مفتوح" معاً وفتح إشارات مختلفة، فظهرت 5 مفتوحة لحساب تجربة بحد 3.
الآن القرار كله (قراءة المفتوح + الفتح + الحفظ) داخل قفل معاملة استشاري على المستخدم، فتتسلسل الطلبات.
"""
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.signal_unlock import SignalUnlock
from app.models.site_settings import SiteSettings
from app.services.decision_grouping import decision_key

_LOCK_NS = 90210010   # مساحة مفاتيح الأقفال الاستشارية لهذه الحصة (90210008/9 لـinit_db)


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


def _lock_user(db: Session, user_id: int) -> None:
    """قفل معاملة على المستخدم — يُحرَّر تلقائياً عند commit/rollback. Postgres فقط (الاختبارات على SQLite بطلب واحد)."""
    bind = db.get_bind()
    if bind is not None and bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(:ns, :uid)"), {"ns": _LOCK_NS, "uid": int(user_id)})


def unlocked_today(db: Session, user_id: int) -> set:
    rows = db.query(SignalUnlock.decision_key).filter(
        SignalUnlock.user_id == user_id, SignalUnlock.day == _today()).all()
    return {r[0] for r in rows}


def open_batch(db: Session, user_id: int, sigs: list, channel: str, limit: int = None) -> list:
    """يقرر لقائمة إشارات دفعة واحدة تحت القفل: المفتوح اليوم يبقى مفتوحاً، وما تبقّى من الحصة يُعطى بترتيب القائمة.
    يُرجع قائمة True/False بنفس ترتيب `sigs`. المستدعي يمرّرها الأحدث أولاً (كترتيب /latest) فيكون الاختيار واحداً
    مهما كان حجم القائمة المطلوبة."""
    limit = daily_limit(db) if limit is None else limit
    if limit <= 0:
        return [True] * len(sigs)
    _lock_user(db, user_id)
    opened = unlocked_today(db, user_id)
    result, day = [], _today()
    for s in sigs:
        k = key_of(s)
        if k in opened:
            result.append(True)
        elif len(opened) < limit:
            db.add(SignalUnlock(user_id=user_id, decision_key=k, day=day, channel=channel,
                                signal_id=getattr(s, "id", None)))
            opened.add(k)
            result.append(True)
        else:
            result.append(False)
    try:
        db.commit()                 # يحرّر القفل
    except IntegrityError:          # احتياط فقط — القفل يمنع التزامن لنفس المستخدم
        db.rollback()
    return result


def try_unlock(db: Session, user_id: int, sig, channel: str, limit: int = None) -> bool:
    return open_batch(db, user_id, [sig], channel, limit)[0]
