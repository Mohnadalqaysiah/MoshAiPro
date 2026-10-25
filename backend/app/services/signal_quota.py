"""
الحصة اليومية للإشارات الكاملة — مصدر واحد للموقع وتيليجرام.

(2026-10-25، قرار المالك "نفّذ") **ثلاث فئات، والحد لكل فئة يضبطه المالك من اللوحة (الإعدادات ← الحدود):**
  - full           أدمن، أو اشتراك مدفوع **فعّال** (subscription_ends_at > الآن) ← كل الإشارات كاملة دائماً.
  - trial_active   تجربة لم ينتهِ أسبوعها ← `trial_active_signal_daily_limit` (افتراضي 0 = بلا حد = كل شيء كامل).
  - trial_expired  تجربة انتهت، أو اشتراك مدفوع انتهى ← `trial_signal_daily_limit` (القيمة القائمة، 5 بالإنتاج).
  الحالة المحفوظة `plan` لا تكفي: الاشتراك المنتهي كان يبقى WEEKLY/MONTHLY (يُخفَّض كسولاً فقط عند طلب تحليل) فيستلم كل
  شيء كاملاً بلا نهاية. الفئة تُحسب من التواريخ.

القاعدة لمن عليه حد: يفتح حتى الحد **قراراً مختلفاً** كل يوم UTC؛ المفتوح يبقى مفتوحاً بالقناتين حتى نهاية اليوم ولا يُعدّ
مرتين. (2026-10-25، بعد حادثة اليوم — 3 حسابات جديدة استهلكت حصتها كاملة لحظة فتح الداشبورد على إشارات الجمعة):
  1. **فتح الموقع لا يستهلك**: /signals/latest يقرأ فقط (consume=False)؛ الفتح بضغط المستخدم (/signals/{id}/unlock)
     أو بإشارة تيليجرام عند وصولها.
  2. **الإشارة المعاد إصدارها تُحسب مرة**: نفس الرمز والفريم والاتجاه ودخول ضمن 1% من مفتوحٍ اليوم ← مفتوحة بلا خصم.
  3. **إشارة سوقها مغلق لا تُفتح ضمن الحصة** (لا تُستهلك فتحة على ما لا يمكن تداوله).

قفل لكل مستخدم: الداشبورد يطلب /latest من 4 مكوّنات معاً — القرار كله داخل قفل معاملة استشاري على المستخدم.
"""
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.signal_unlock import SignalUnlock
from app.models.site_settings import SiteSettings
from app.services.decision_grouping import decision_key

_LOCK_NS = 90210010   # مساحة مفاتيح الأقفال الاستشارية لهذه الحصة (90210008/9 لـinit_db)
REISSUE_PCT = 0.01    # (2026-10-25) 1% للحصة وحدها: حالتا 25/10 الحقيقيتان كانتا 0.52% (NFLX) و0.8% (EMIRATESNBD) فتفوتهما
                      # عتبة merge_reissued (0.5%، للتقارير — لا تُمس). نفس الرمز والفريم والاتجاه بنفس اليوم.
TIER_KEYS = {
    "trial_active":  ("trial_active_signal_daily_limit", 0),
    "trial_expired": ("trial_signal_daily_limit", 3),
}


def _aware(d):
    return d if d is None or d.tzinfo else d.replace(tzinfo=timezone.utc)


def tier_of(user, now: datetime = None) -> str:
    from app.models.user import PlanType, UserRole
    now = now or datetime.now(timezone.utc)
    if getattr(user, "role", None) == UserRole.ADMIN:
        return "full"
    plan = getattr(user, "plan", None)
    if plan in (PlanType.WEEKLY, PlanType.MONTHLY):
        ends = _aware(getattr(user, "subscription_ends_at", None))
        return "full" if ends and ends > now else "trial_expired"
    if plan == PlanType.TRIAL:
        ends = _aware(getattr(user, "trial_ends_at", None))
        return "trial_active" if ends is None or ends > now else "trial_expired"
    return "trial_expired"


def has_full_access(user) -> bool:
    return tier_of(user) == "full"


def _setting_int(db: Session, key: str, default: int) -> int:
    row = db.query(SiteSettings).filter(SiteSettings.key == key).first()
    try:
        return int(row.value) if row and str(row.value).strip() != "" else default
    except Exception:
        return default


def daily_limit(db: Session) -> int:
    """حد التجربة المنتهية (المفتاح القائم) — للتوافق مع المستدعين القدامى."""
    return _setting_int(db, *TIER_KEYS["trial_expired"])


def limit_for(db: Session, user) -> int:
    """الحد اليومي لفئة المستخدم. 0 = بلا حد (كل الإشارات كاملة)."""
    tier = tier_of(user)
    if tier == "full":
        return 0
    return _setting_int(db, *TIER_KEYS[tier])


def key_of(sig) -> str:
    m, tf, st, e = decision_key(sig.market, sig.timeframe, sig.signal_type, sig.entry_price)
    return f"{m}|{tf}|{st}|{e}"


def _same_idea(k1: str, k2: str) -> bool:
    """نفس الرمز والفريم والاتجاه، ودخول ضمن REISSUE_PCT — صفقة أُعيد إصدارها لا فكرة جديدة."""
    a, b = k1.split("|"), k2.split("|")
    if len(a) != 4 or len(b) != 4 or a[:3] != b[:3]:
        return False
    try:
        e1, e2 = float(a[3]), float(b[3])
    except ValueError:
        return False
    return e1 == e2 or (max(e1, e2) > 0 and abs(e1 - e2) / max(e1, e2) <= REISSUE_PCT)


def _is_open_today(k: str, opened: set) -> bool:
    return k in opened or any(_same_idea(k, o) for o in opened)


def _market_open(market: str) -> bool:
    try:
        from app.services.smart_data import smart_data
        return bool(smart_data.is_market_open(market))
    except Exception:
        return True


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


def open_batch(db: Session, user_id: int, sigs: list, channel: str, limit: int = None, consume: bool = True) -> list:
    """يقرر لقائمة إشارات تحت القفل: المفتوح اليوم (أو نسخته المعاد إصدارها) مفتوح؛ وإن consume=True يُعطى ما تبقّى من
    الحصة بترتيب القائمة لإشارات أسواقها مفتوحة. consume=False = قراءة فقط (عرض الموقع). يُرجع True/False بترتيب sigs."""
    limit = daily_limit(db) if limit is None else limit
    if limit <= 0:
        return [True] * len(sigs)
    _lock_user(db, user_id)
    opened = unlocked_today(db, user_id)
    result, day, added = [], _today(), False
    for s in sigs:
        k = key_of(s)
        if _is_open_today(k, opened):
            result.append(True)
        elif consume and len(opened) < limit and _market_open(s.market):
            db.add(SignalUnlock(user_id=user_id, decision_key=k, day=day, channel=channel,
                                signal_id=getattr(s, "id", None)))
            opened.add(k)
            added = True
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


def quota_status(db: Session, user) -> dict:
    """للواجهة: الفئة والحد والمستخدم اليوم والمتبقي (limit=0 ← بلا حد)."""
    tier = tier_of(user)
    limit = limit_for(db, user)
    used = len(unlocked_today(db, user.id)) if limit > 0 else 0
    return {"tier": tier, "limit": limit, "used": used, "remaining": max(0, limit - used) if limit > 0 else None}
