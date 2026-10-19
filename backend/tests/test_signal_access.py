"""
اختبارات الوصول لتفاصيل الإشارات (2026-10-19):
  - إغلاق ثغرة /signals/{id} (كانت بلا مصادقة فتكشف اتجاه ومستويات كل إشارة نشطة لأي زائر)
  - /signals/latest: قرار واحد لكل إشارة، والمموّهة بلا اتجاه ولا ثقة
  - الحصة اليومية الموحّدة بين الموقع وتيليجرام (signal_quota) — على قاعدة SQLite حقيقية بالذاكرة
  - زر "آخر الإشارات" بالبوت باسم المستخدم المرتبط

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
from app.database import Base  # noqa: E402
from app.models.signal import Signal, SignalStatus  # noqa: E402
from app.models.signal_unlock import SignalUnlock  # noqa: E402
from app.models.site_settings import SiteSettings  # noqa: E402
from app.models.user import PlanType, User, UserRole  # noqa: E402
from app.services.auth_service import get_current_user  # noqa: E402

E = lambda v: SimpleNamespace(value=v)  # noqa: E731


def _sig(i=0, status=SignalStatus.ACTIVE, user_id=1, market="XAUUSD", entry=None):
    return SimpleNamespace(
        id=100 + i, market=market, timeframe="4h", user_id=user_id, entry_price=entry if entry is not None else 2400.0 + i,
        stop_loss=2410.0, take_profit_1=2385.0, take_profit_2=2370.0, current_price=2398.0, ai_confidence=78,
        ai_reasoning="سبب", wyckoff_phase=None, premium_discount=None, killzone=None, risk_reward_ratio=1.5,
        profit_loss=None, profit_loss_percentage=None, notes=None,
        created_at=datetime(2026, 10, 19, tzinfo=timezone.utc), expires_at=None,
        signal_type=E("SELL"), signal_quality=E("A"), status=status,
    )


class _Rows:
    """استعلام Signal/User المزيّف — يرجع القائمة كما هي (مرتبة الأحدث أولاً كما يرتبها المسار)."""
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
    """Signal وUser مزيّفان؛ signal_unlocks وsite_settings على SQLite حقيقية (العدّ والتفرّد يُختبران فعلاً)."""
    def __init__(self, signals=(), users=(), free=None):
        eng = create_engine("sqlite://")
        Base.metadata.create_all(eng, tables=[SignalUnlock.__table__, SiteSettings.__table__])
        self.s = sessionmaker(bind=eng)()
        self.engine = eng
        self.signals, self.users = list(signals), list(users)
        if free is not None:
            self.s.add(SiteSettings(key="trial_signal_daily_limit", value=str(free)))
            self.s.commit()

    def query(self, *ents):
        e = ents[0]
        owner = getattr(e, "class_", e)
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


def _user(uid=2, plan=PlanType.TRIAL, role=UserRole.USER, tg="777"):
    return SimpleNamespace(id=uid, plan=plan, role=role, telegram_id=tg)


def _detail(db, sig, user):
    db.signals = [sig]
    return asyncio.run(S.get_signal_details(signal_id=sig.id, user=user, db=db))["data"]


def _latest(db, user, limit=10):
    return asyncio.run(S.get_latest_signals(limit=limit, hours=12, user=user, db=db))["data"]


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
    for u in (_user(plan=PlanType.MONTHLY), _user(plan=PlanType.WEEKLY), _user(role=UserRole.ADMIN)):
        assert _detail(db, _sig(), u)["locked"] is False
    assert db.unlock_count() == 0


def test_detail_trial_quota_and_masked_has_no_direction():
    db, u = _DB(free=3), _user()
    for i in range(3):
        assert _detail(db, _sig(i), u)["locked"] is False
    d = _detail(db, _sig(3), u)                               # الرابعة بعد نفاد الحصة
    assert d["locked"] is True
    for k in ("signal_type", "entry_price", "stop_loss", "take_profit_1", "take_profit_2", "ai_confidence", "ai_reasoning"):
        assert k not in d, k
    assert _detail(db, _sig(0), u)["locked"] is False         # ما فُتح يبقى مفتوحاً ولا يُعدّ ثانية
    assert db.unlock_count() == 3


def test_own_watch_copy_does_not_bypass_quota():
    """تنبيه المراقبة يُنشئ صفاً باسم المستخدم قبل قرار الحصة — من وصله مموّهاً لا يجد المستويات هنا."""
    db, u = _DB(free=1), _user(uid=2)
    assert _detail(db, _sig(0), u)["locked"] is False
    assert _detail(db, _sig(1, user_id=2), u)["locked"] is True


# ─── /signals/latest ─────────────────────────────────────────────────────────
def test_latest_trial_opens_newest_first_and_masks_rest_without_direction():
    db = _DB(signals=[_sig(i) for i in range(5)], free=3)    # 100 الأحدث … 104 الأقدم
    d = _latest(db, _user())
    assert [x["id"] for x in d if not x["locked"]] == [100, 101, 102]
    for x in d:
        if x["locked"]:
            for k in ("recommendation", "signal_type", "ai_confidence", "ai_confidence_score", "entry_price",
                      "stop_loss", "take_profit_1", "take_profit_2", "risk_reward_ratio"):
                assert x[k] is None, k
            assert x["market"] == "XAUUSD" and x["timeframe"] == "4h"
        else:
            assert x["signal_type"] == "SELL" and x["ai_confidence"] == 78 and x["entry_price"] >= 2400.0


def test_latest_opened_signal_stays_open_when_newer_arrive():
    """بلاغ المالك ضمنياً: قبل التوحيد كانت إشارة رآها مفتوحة تُقفل حين تصدر 3 أحدث منها."""
    db, u = _DB(signals=[_sig(i) for i in range(3)], free=3), _user()
    assert not any(x["locked"] for x in _latest(db, u))
    db.signals = [_sig(i) for i in range(10, 13)] + db.signals   # 3 إشارات أحدث
    d = {x["id"]: x["locked"] for x in _latest(db, u)}
    assert d == {110: True, 111: True, 112: True, 100: False, 101: False, 102: False}
    assert db.unlock_count() == 3


def test_latest_different_list_sizes_open_same_decisions():
    """بلاغ ما بعد النشر: 4 مكوّنات بأحجام مختلفة (10/50/200) فتحت 5 إشارات لحساب بحد 3."""
    db, u = _DB(signals=[_sig(i) for i in range(8)], free=3), _user()
    for lim in (2, 200, 10, 50, 1):
        _latest(db, u, limit=lim)
    assert db.unlock_count() == 3
    assert [x["id"] for x in _latest(db, u, limit=200) if not x["locked"]] == [100, 101, 102]


def test_quota_uses_user_lock_on_postgres():
    """القفل نفسه لا يُختبر على SQLite — نتحقق أنه يُطلب بمفتاح المستخدم حين تكون القاعدة Postgres."""
    from app.services import signal_quota as Q
    calls = []
    fake = SimpleNamespace(get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name="postgresql")),
                           execute=lambda sql, params: calls.append((str(sql), params)))
    Q._lock_user(fake, 138)
    assert calls and "pg_advisory_xact_lock" in calls[0][0] and calls[0][1]["uid"] == 138


def test_latest_repeat_calls_do_not_consume_more():
    db, u = _DB(signals=[_sig(i) for i in range(5)], free=3), _user()
    for _ in range(4):
        _latest(db, u)
    assert db.unlock_count() == 3


def test_latest_subscriber_and_unlimited_see_all():
    db = _DB(signals=[_sig(i) for i in range(5)], free=3)
    assert not any(x["locked"] for x in _latest(db, _user(plan=PlanType.MONTHLY)))
    db0 = _DB(signals=[_sig(i) for i in range(5)], free=0)   # 0 = بلا حد من الإعدادات
    assert not any(x["locked"] for x in _latest(db0, _user()))
    assert db.unlock_count() == 0 and db0.unlock_count() == 0


def test_latest_dedupes_copies_of_same_decision():
    """بلاغ المالك: نفس إشارة NAS100 ظهرت 8 مرات (صف لكل مشترك) فاستهلكت الحصة ثم ظهرت مقفلة بجانب نفسها."""
    copies = [_sig(i, entry=2400.0, user_id=10 + i) for i in range(6)]   # نفس القرار، 6 مشتركين
    other = [_sig(20 + i, market="BTCUSD", entry=100.0 + i) for i in range(2)]
    db = _DB(signals=copies[:3] + other[:1] + copies[3:] + other[1:], free=3)
    d = _latest(db, _user())
    assert [x["id"] for x in d] == [100, 120, 121]           # قرار واحد لكل إشارة، بترتيبها
    assert not any(x["locked"] for x in d)                   # 3 قرارات فريدة = كلها ضمن الحصة


def test_yesterday_unlocks_do_not_count_today():
    db, u = _DB(signals=[_sig(i) for i in range(3)], free=3), _user()
    y = datetime.now(timezone.utc).date() - timedelta(days=1)
    for i in range(3):
        db.s.add(SignalUnlock(user_id=2, decision_key=f"OLD|4h|SELL|{i}", day=y, channel="web"))
    db.s.commit()
    assert not any(x["locked"] for x in _latest(db, u))      # حصة اليوم كاملة من جديد


# ─── التوحيد مع تيليجرام ─────────────────────────────────────────────────────
def _consume(db, signal_id):
    import app.api.bot as B
    return B.bot_consume_signal_notification(telegram_id="777", signal_id=signal_id, _=True, db=db)


def test_telegram_and_web_share_one_quota():
    sigs = [_sig(i) for i in range(5)]
    u = _user()
    db = _DB(signals=sigs, users=[u], free=3)
    db.signals = [sigs[0]]
    assert _consume(db, 100)["unlocked"] is True             # وصلته كاملة على تيليجرام
    db.signals = sigs
    d = {x["id"]: x["locked"] for x in _latest(db, u)}
    assert d[100] is False                                   # نفس الإشارة مفتوحة بالموقع
    assert sum(1 for v in d.values() if not v) == 3          # والحصة 3 لا 4
    db.signals = [sigs[3]]
    assert _consume(db, 103)["unlocked"] is False            # نفدت الحصة بالقناتين
    db.signals = [sigs[2]]
    assert _consume(db, 102)["unlocked"] is True             # فتحها الموقع ← تصل كاملة على تيليجرام بلا خصم
    assert db.unlock_count() == 3


def test_bot_latest_signals_uses_linked_user():
    """زر "آخر الإشارات" بالبوت: كان يرجع 401 دائماً (مفتاح البوت بدل توكن مستخدم). الآن باسم المستخدم المرتبط."""
    import app.api.bot as B
    db = _DB(signals=[_sig(i) for i in range(5)], free=3)
    o_link = B._get_linked_user
    try:
        B._get_linked_user = lambda tg, db: None
        assert asyncio.run(B.bot_latest_signals(telegram_id="1", limit=8, _=True, db=db)) == {"linked": False, "data": []}
        B._get_linked_user = lambda tg, db: _user()
        r = asyncio.run(B.bot_latest_signals(telegram_id="1", limit=8, _=True, db=db))
        assert r["linked"] and sum(1 for x in r["data"] if not x["locked"]) == 3
        assert all(x["signal_type"] is None for x in r["data"] if x["locked"])
        B._get_linked_user = lambda tg, db: _user(plan=PlanType.WEEKLY)
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
