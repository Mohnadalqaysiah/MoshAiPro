"""
اختبارات الوصول لتفاصيل الإشارات والحصة اليومية:
  - /signals/{id} يتطلب تسجيل الدخول؛ النشطة مموّهة لمن نفدت حصته (ثغرة 19/10)
  - /signals/latest: قرار واحد لكل إشارة، والمموّهة بلا اتجاه ولا ثقة
  - (2026-10-25) ثلاث فئات: مشترك فعّال (كامل)، تجربة نشطة (حد من اللوحة، افتراضي بلا حد)، تجربة/اشتراك منتهٍ (حد من اللوحة)
  - (2026-10-25) عرض الموقع لا يستهلك الحصة؛ الفتح بضغطة (/unlock) أو بوصول الإشارة على تيليجرام؛ المعاد إصدارها تُحسب مرة؛
    سوق مغلق لا يُفتح ضمن الحصة
  - الحصة موحّدة بين الموقع وتيليجرام — على قاعدة SQLite حقيقية بالذاكرة

  cd backend && python tests/test_signal_access.py      (أو pytest)
"""
import asyncio
import inspect
import os
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@127.0.0.1:1/x")


class _Stub(types.ModuleType):
    def __getattr__(self, n):
        if n.startswith("__"):
            raise AttributeError(n)
        return type(n, (), {"__init__": lambda self, *a, **k: None})


for _m in ("telegram", "telegram.ext", "telegram.constants", "telegram.error"):
    sys.modules.setdefault(_m, _Stub(_m))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import app.api.signals as S  # noqa: E402
import app.services.signal_quota as Q  # noqa: E402
from app.database import Base  # noqa: E402
from app.models.signal import Signal, SignalStatus  # noqa: E402
from app.models.signal_unlock import SignalUnlock  # noqa: E402
from app.models.site_settings import SiteSettings  # noqa: E402
from app.models.user import PlanType, User, UserRole  # noqa: E402
from app.services.auth_service import get_current_user  # noqa: E402

E = lambda v: SimpleNamespace(value=v)  # noqa: E731
NOW = datetime.now(timezone.utc)
CLOSED_MARKETS: set = set()
Q._market_open = lambda m: m not in CLOSED_MARKETS     # الاختبارات لا تعتمد على يوم تشغيلها


def _sig(i=0, status=SignalStatus.ACTIVE, user_id=1, market="XAUUSD", entry=None):
    return SimpleNamespace(
        id=100 + i, market=market, timeframe="4h", user_id=user_id,
        entry_price=entry if entry is not None else round(2400.0 * (1 + 0.03 * i), 5),   # 3% بين كل إشارة: أفكار مختلفة
        stop_loss=2410.0, take_profit_1=2385.0, take_profit_2=2370.0, current_price=2398.0, ai_confidence=78,
        ai_reasoning="سبب", wyckoff_phase=None, premium_discount=None, killzone=None, risk_reward_ratio=1.5,
        profit_loss=None, profit_loss_percentage=None, notes=None,
        created_at=datetime(2026, 10, 19, tzinfo=timezone.utc), expires_at=None,
        signal_type=E("SELL"), signal_quality=E("A"), status=status,
    )


class _Rows:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *a, **k):
        return self

    def order_by(self, *a):
        return self

    def limit(self, *a):
        return self

    def all(self):
        return self.rows

    def first(self):
        return self.rows[0] if self.rows else None


class _DB:
    """Signal وUser مزيّفان؛ signal_unlocks وsite_settings على SQLite حقيقية."""
    def __init__(self, signals=(), users=(), free=None, active_limit=None):
        eng = create_engine("sqlite://")
        Base.metadata.create_all(eng, tables=[SignalUnlock.__table__, SiteSettings.__table__])
        self.s = sessionmaker(bind=eng)()
        self.engine = eng
        self.signals, self.users = list(signals), list(users)
        for k, v in (("trial_signal_daily_limit", free), ("trial_active_signal_daily_limit", active_limit)):
            if v is not None:
                self.s.add(SiteSettings(key=k, value=str(v)))
        self.s.commit()

    def query(self, *ents):
        owner = getattr(ents[0], "class_", ents[0])
        if owner is Signal:
            return _Rows(self.signals)
        if owner is User:
            return _Rows(self.users)
        return self.s.query(*ents)

    def get_bind(self):
        return self.engine

    def add(self, o):
        self.s.add(o)

    def commit(self):
        self.s.commit()

    def rollback(self):
        self.s.rollback()

    def unlock_count(self, user_id=2):
        return self.s.query(SignalUnlock).filter(SignalUnlock.user_id == user_id).count()


def _user(uid=2, plan=PlanType.TRIAL, role=UserRole.USER, tg="777", trial_days=-1, sub_days=None):
    """الافتراضي: تجربة **منتهية** (عليها الحد). trial_days>0 = تجربة نشطة. sub_days = نهاية اشتراك مدفوع."""
    return SimpleNamespace(id=uid, plan=plan, role=role, telegram_id=tg,
                           trial_ends_at=NOW + timedelta(days=trial_days),
                           subscription_ends_at=(NOW + timedelta(days=sub_days)) if sub_days is not None else None)


def _paid(plan=PlanType.MONTHLY, days=10):
    return _user(plan=plan, sub_days=days)


def _detail(db, sig, user):
    db.signals = [sig]
    return asyncio.run(S.get_signal_details(signal_id=sig.id, user=user, db=db))["data"]


def _latest_full(db, user, limit=10):
    return asyncio.run(S.get_latest_signals(limit=limit, hours=12, user=user, db=db))


def _latest(db, user, limit=10):
    return _latest_full(db, user, limit)["data"]


def _unlock(db, sig, user):
    keep = db.signals
    db.signals = [sig]
    try:
        return S.unlock_signal(signal_id=sig.id, user=user, db=db)
    finally:
        db.signals = keep


# ─── الفئات (2026-10-25) ─────────────────────────────────────────────────────
def test_tiers_from_dates_not_saved_plan():
    assert Q.tier_of(_user(role=UserRole.ADMIN)) == "full"
    assert Q.tier_of(_paid(days=5)) == "full"
    assert Q.tier_of(_paid(days=-1)) == "trial_expired"            # اشتراك انتهى وplan ما زالت MONTHLY
    assert Q.tier_of(_paid(PlanType.WEEKLY, days=-2)) == "trial_expired"
    assert Q.tier_of(_user(trial_days=3)) == "trial_active"
    assert Q.tier_of(_user(trial_days=-1)) == "trial_expired"


def test_limits_per_tier_from_settings():
    db = _DB(free=5)
    assert Q.limit_for(db, _user(trial_days=3)) == 0               # تجربة نشطة: افتراضي بلا حد
    assert Q.limit_for(db, _user()) == 5
    assert Q.limit_for(db, _paid()) == 0
    db2 = _DB(free=2, active_limit=10)
    assert Q.limit_for(db2, _user(trial_days=3)) == 10 and Q.limit_for(db2, _user()) == 2


def test_active_trial_sees_everything_by_default():
    db = _DB(signals=[_sig(i) for i in range(6)], free=3)
    d = _latest(db, _user(trial_days=4))
    assert not any(x["locked"] for x in d) and all(x["signal_type"] == "SELL" for x in d)
    assert db.unlock_count() == 0


def test_expired_paid_subscriber_gets_limit_not_full():
    db = _DB(signals=[_sig(i) for i in range(4)], free=2)
    assert all(x["locked"] for x in _latest(db, _paid(days=-3)))


# ─── /signals/{id} ───────────────────────────────────────────────────────────
def test_requires_login():
    dep = inspect.signature(S.get_signal_details).parameters["user"].default
    assert getattr(dep, "dependency", None) is get_current_user


def test_closed_visible_to_any_logged_in_without_consuming_quota():
    db = _DB(free=3)
    for st in (SignalStatus.TP1_HIT, SignalStatus.SL_HIT, SignalStatus.BREAKEVEN, SignalStatus.EXPIRED):
        d = _detail(db, _sig(status=st), _user())
        assert d["locked"] is False and d["entry_price"] == 2400.0
    assert db.unlock_count() == 0


def test_active_full_for_subscriber_and_admin_without_quota():
    db = _DB(free=3)
    for u in (_paid(), _paid(PlanType.WEEKLY), _user(role=UserRole.ADMIN)):
        assert _detail(db, _sig(), u)["locked"] is False
    assert db.unlock_count() == 0


def test_detail_link_consumes_and_masked_has_no_direction():
    """فتح إشارة من رابط (زر عرض في حسابي) فعل صريح ← يستهلك فتحة."""
    db, u = _DB(free=3), _user()
    for i in range(3):
        assert _detail(db, _sig(i), u)["locked"] is False
    d = _detail(db, _sig(3), u)
    assert d["locked"] is True
    for k in ("signal_type", "entry_price", "stop_loss", "take_profit_1", "take_profit_2", "ai_confidence", "ai_reasoning"):
        assert k not in d, k
    assert _detail(db, _sig(0), u)["locked"] is False
    assert db.unlock_count() == 3


def test_own_watch_copy_does_not_bypass_quota():
    db, u = _DB(free=1), _user(uid=2)
    assert _detail(db, _sig(0), u)["locked"] is False
    assert _detail(db, _sig(1, user_id=2), u)["locked"] is True


# ─── /signals/latest: العرض لا يستهلك (2026-10-25) ──────────────────────────
def test_viewing_latest_consumes_nothing():
    """حادثة 25/10: 3 حسابات جديدة فقدت حصتها كاملة لحظة فتح الداشبورد."""
    db, u = _DB(signals=[_sig(i) for i in range(8)], free=3), _user()
    for lim in (2, 200, 10, 50, 1):
        d = _latest(db, u, limit=lim)
    assert db.unlock_count() == 0
    assert all(x["locked"] and x["can_unlock"] for x in d)
    full = _latest_full(db, u)
    assert full["quota"] == {"tier": "trial_expired", "limit": 3, "used": 0, "remaining": 3}
    for x in full["data"]:
        for k in ("recommendation", "signal_type", "ai_confidence", "entry_price", "stop_loss", "take_profit_1"):
            assert x[k] is None, k


def test_unlock_by_tap_respects_quota():
    sigs = [_sig(i) for i in range(5)]
    db, u = _DB(signals=sigs, free=3), _user()
    for i in range(3):
        assert _unlock(db, sigs[i], u)["unlocked"] is True
    r = _unlock(db, sigs[3], u)
    assert r["unlocked"] is False and r["reason"] == "quota_exhausted" and r["quota"]["remaining"] == 0
    d = {x["id"]: x for x in _latest(db, u)}
    assert [i for i, x in d.items() if not x["locked"]] == [100, 101, 102]
    assert d[103]["can_unlock"] is False                           # نفدت الحصة
    assert _unlock(db, sigs[0], u)["unlocked"] is True and db.unlock_count() == 3   # المفتوح لا يُعدّ ثانية


def test_reissued_signal_counts_once():
    """حالتا 25/10: نتفليكس 66.587/66.935 (0.52%) والإمارات دبي الوطني 29.77/30.01 (0.8%) = فكرة واحدة لكلٍّ."""
    a = _sig(0, market="NFLX", entry=66.5874)
    b = _sig(1, market="NFLX", entry=66.935)
    c = _sig(2, market="NFLX", entry=70.0)                         # 5% بعيداً: فكرة أخرى
    db, u = _DB(signals=[a, b, c], free=3), _user()
    assert _unlock(db, a, u)["unlocked"] is True
    d = {x["id"]: x["locked"] for x in _latest(db, u)}
    assert d == {100: False, 101: False, 102: True} and db.unlock_count() == 1
    e1, e2 = _sig(5, market="EMIRATESNBD", entry=29.77), _sig(6, market="EMIRATESNBD", entry=30.01)
    db2 = _DB(signals=[e1, e2], free=3)
    assert _unlock(db2, e2, u)["unlocked"] and all(not x["locked"] for x in _latest(db2, u)) and db2.unlock_count() == 1


def test_closed_market_not_unlocked_within_quota():
    CLOSED_MARKETS.add("EMIRATESNBD")
    try:
        s = _sig(0, market="EMIRATESNBD", entry=29.77)
        db, u = _DB(signals=[s], free=3), _user()
        r = _unlock(db, s, u)
        assert r["unlocked"] is False and r["reason"] == "market_closed" and db.unlock_count() == 0
        x = _latest(db, u)[0]
        assert x["locked"] and not x["can_unlock"] and x["market_open"] is False
    finally:
        CLOSED_MARKETS.discard("EMIRATESNBD")


def test_opened_signal_stays_open_when_newer_arrive():
    sigs = [_sig(i) for i in range(3)]
    db, u = _DB(signals=sigs, free=3), _user()
    for s in sigs:
        _unlock(db, s, u)
    db.signals = [_sig(i) for i in range(10, 13)] + sigs
    d = {x["id"]: x["locked"] for x in _latest(db, u)}
    assert d == {110: True, 111: True, 112: True, 100: False, 101: False, 102: False}


def test_quota_uses_user_lock_on_postgres():
    calls = []
    fake = SimpleNamespace(get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name="postgresql")),
                           execute=lambda sql, params: calls.append((str(sql), params)))
    Q._lock_user(fake, 138)
    assert calls and "pg_advisory_xact_lock" in calls[0][0] and calls[0][1]["uid"] == 138


def test_latest_dedupes_copies_of_same_decision():
    copies = [_sig(i, entry=2400.0, user_id=10 + i) for i in range(6)]
    other = [_sig(20 + i, market="BTCUSD", entry=100.0 + 10 * i) for i in range(2)]
    db = _DB(signals=copies[:3] + other[:1] + copies[3:] + other[1:], free=3)
    assert [x["id"] for x in _latest(db, _user())] == [100, 120, 121]


def test_yesterday_unlocks_do_not_count_today():
    sigs = [_sig(i) for i in range(3)]
    db, u = _DB(signals=sigs, free=3), _user()
    y = NOW.date() - timedelta(days=1)
    for i in range(3):
        db.s.add(SignalUnlock(user_id=2, decision_key=f"OLD|4h|SELL|{i}", day=y, channel="web"))
    db.s.commit()
    assert all(_unlock(db, s, u)["unlocked"] for s in sigs)


# ─── التوحيد مع تيليجرام ─────────────────────────────────────────────────────
def _consume(db, signal_id):
    import app.api.bot as B
    return B.bot_consume_signal_notification(telegram_id="777", signal_id=signal_id, _=True, db=db)


def test_telegram_and_web_share_one_quota():
    sigs = [_sig(i) for i in range(5)]
    u = _user()
    db = _DB(signals=sigs, users=[u], free=3)
    db.signals = [sigs[0]]
    assert _consume(db, 100)["unlocked"] is True                   # وصلته كاملة على تيليجرام
    db.signals = sigs
    assert {x["id"] for x in _latest(db, u) if not x["locked"]} == {100}   # ومفتوحة بالموقع
    assert _unlock(db, sigs[1], u)["unlocked"] and _unlock(db, sigs[2], u)["unlocked"]
    db.signals = [sigs[3]]
    assert _consume(db, 103)["unlocked"] is False                  # نفدت الحصة بالقناتين
    db.signals = [sigs[2]]
    assert _consume(db, 102)["unlocked"] is True                   # فتحها الموقع ← تيليجرام بلا خصم
    assert db.unlock_count() == 3


def test_telegram_active_trial_unlimited_by_default():
    u = _user(trial_days=5)
    db = _DB(signals=[_sig(0)], users=[u], free=3)
    for _ in range(10):
        assert _consume(db, 100)["unlocked"] is True
    assert db.unlock_count() == 0


def test_bot_latest_signals_uses_linked_user():
    import app.api.bot as B
    db = _DB(signals=[_sig(i) for i in range(5)], free=3)
    o_link = B._get_linked_user
    try:
        B._get_linked_user = lambda tg, db: None
        assert asyncio.run(B.bot_latest_signals(telegram_id="1", limit=8, _=True, db=db)) == {"linked": False, "data": []}
        B._get_linked_user = lambda tg, db: _user()
        r = asyncio.run(B.bot_latest_signals(telegram_id="1", limit=8, _=True, db=db))
        assert r["linked"] and all(x["locked"] and x["signal_type"] is None for x in r["data"])
        B._get_linked_user = lambda tg, db: _paid(PlanType.WEEKLY)
        r = asyncio.run(B.bot_latest_signals(telegram_id="1", limit=8, _=True, db=db))
        assert not any(x["locked"] for x in r["data"])
    finally:
        B._get_linked_user = o_link


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
