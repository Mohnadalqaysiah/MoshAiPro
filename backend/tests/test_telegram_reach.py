"""
اختبارات "من حظر البوت" (2026-10-19) — services/telegram_reach.py ومساراته.
قياس 17-19/10: 147 مستخدماً حظروا البوت ← 5414 إرسالاً فاشلاً في يومين.

  cd backend && python tests/test_telegram_reach.py      (أو pytest)
"""
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

from app.database import Base  # noqa: E402
from app.models.user import PlanType, User  # noqa: E402
from app.services import telegram_reach as T  # noqa: E402

NOW = datetime.now(timezone.utc)


def _db(users):
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng, tables=[User.__table__])
    s = sessionmaker(bind=eng)()
    for i, (tg, blocked_at) in enumerate(users, start=1):
        s.add(User(id=i, email=f"u{i}@x.com", telegram_id=tg, is_active=True,
                   plan=PlanType.TRIAL, telegram_blocked_at=blocked_at))
    s.commit()
    return s


def _blocked(s, tg):
    return s.query(User).filter(User.telegram_id == tg).first().telegram_blocked_at


def test_error_markers():
    assert T.is_unreachable("Forbidden: bot was blocked by the user")
    assert T.is_unreachable("Forbidden: user is deactivated")
    assert T.is_unreachable("Bad Request: chat not found")
    assert not T.is_unreachable("Too Many Requests: retry after 5")   # مشكلة سرعة لا حظر — لا يُستبعد
    assert not T.is_unreachable(None) and not T.is_unreachable("")


def test_should_skip_window():
    assert not T.should_skip(SimpleNamespace(telegram_blocked_at=None))
    assert T.should_skip(SimpleNamespace(telegram_blocked_at=NOW - timedelta(days=1)))
    assert not T.should_skip(SimpleNamespace(telegram_blocked_at=NOW - timedelta(days=8)))       # محاولة أسبوعية
    assert T.should_skip(SimpleNamespace(telegram_blocked_at=(NOW - timedelta(hours=2)).replace(tzinfo=None)))


def test_apply_results_marks_and_clears():
    s = _db([("1", None), ("2", NOW - timedelta(days=3)), ("3", None)])
    r = T.apply_results(s, [("1", False, "Forbidden: bot was blocked by the user"),
                            ("2", True, None),                                  # فكّ الحظر ووصله
                            ("3", False, "Too Many Requests: retry after 5")])  # لا يُعلَّم
    s.commit()
    assert r == {"blocked": 1, "reached": 1}
    assert _blocked(s, "1") is not None and _blocked(s, "2") is None and _blocked(s, "3") is None


def test_reachable_filter_on_real_query():
    s = _db([("1", None), ("2", NOW - timedelta(days=1)), ("3", NOW - timedelta(days=10))])
    got = {u.telegram_id for u in s.query(User).filter(T.reachable()).all()}
    assert got == {"1", "3"}                                  # 2 محظور حديثاً؛ 3 يُعاد تجربته


def test_mark_seen_unblocks():
    s = _db([("1", NOW)])
    assert T.mark_seen(s, "1") is True and _blocked(s, "1") is None
    assert T.mark_seen(s, "1") is False                       # لا شيء يُفك ثانية


def test_record_deliveries_then_broadcast_list_skips_blocked():
    """المسار الكامل: بث فشل لمحظور ← لا يظهر بقائمة البث التالية؛ يضغط /start ← يرجع."""
    import app.api.bot as B
    s = _db([("1", None), ("2", None)])
    sig = SimpleNamespace(id=5)

    class _DB:
        def query(self, *e):
            if getattr(e[0], "class_", e[0]).__name__ == "Signal":
                return SimpleNamespace(filter=lambda *a: SimpleNamespace(first=lambda: sig))
            return s.query(*e)

        def add(self, o):
            pass                                              # صفوف SignalDelivery لا تهم هنا

        def commit(self):
            s.commit()

    r = B.bot_record_deliveries(signal_id=5, deliveries=[
        {"telegram_id": "1", "ok": True, "variant": "full"},
        {"telegram_id": "2", "ok": False, "variant": "full", "error": "Forbidden: bot was blocked by the user"}],
        _=True, db=_DB())
    assert r["blocked"] == 1
    subs = {x["telegram_id"] for x in B.bot_active_subscribers(_=True, db=s)["subscribers"]}
    assert subs == {"1"}
    B.bot_telegram_seen(telegram_id="2", _=True, db=s)
    subs = {x["telegram_id"] for x in B.bot_active_subscribers(_=True, db=s)["subscribers"]}
    assert subs == {"1", "2"}


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
