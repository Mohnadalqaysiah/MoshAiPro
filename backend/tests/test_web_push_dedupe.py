"""
اختبارات تكرار إشعارات التطبيق (2026-10-31) — web_push_broadcaster الحقيقي مع send_push الحقيقي على قاعدة بيانات، والخارج webpush فقط.

  cd backend && python tests/test_web_push_dedupe.py      (أو pytest)

القرار الواحد صف Signal لكل مستخدم: المطلوب إشعار واحد لكل مستخدم مهما كثرت الصفوف، حتى بين الدورات.
"""
import os
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@127.0.0.1:1/x")

PUSHES = []
_pw = types.ModuleType("pywebpush")
_pw.WebPushException = type("WebPushException", (Exception,), {})
_pw.webpush = lambda subscription_info, data, **k: PUSHES.append((subscription_info["endpoint"], data))
sys.modules["pywebpush"] = _pw

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.database import Base  # noqa: E402
from app.models.notification import Notification  # noqa: E402
from app.models.push_subscription import PushSubscription  # noqa: E402
from app.models.signal import Signal, SignalStatus, SignalType  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services import web_push as WP  # noqa: E402
from app.services import web_push_broadcaster as B  # noqa: E402

WP.push_enabled = lambda: True
NOW = datetime.now(timezone.utc)
_next = [100]


def _db(users=3, **prefs):
    PUSHES.clear()
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng, tables=[User.__table__, Signal.__table__, PushSubscription.__table__, Notification.__table__])
    s = sessionmaker(bind=eng)()
    for i in range(1, users + 1):
        s.add(User(id=i, email=f"u{i}@x.com", password_hash="x", **prefs))
        s.add(PushSubscription(user_id=i, endpoint=f"e{i}", p256dh="p", auth="a"))
    s.commit()
    return s


def _row(s, user_id=1, market="XAUUSD", entry=4160.5, tf="1h", side=SignalType.BUY, status=SignalStatus.ACTIVE, age_min=1, conf=70):
    _next[0] += 1
    s.add(Signal(id=_next[0], user_id=user_id, market=market, timeframe=tf, signal_type=side, status=status,
                 entry_price=entry, stop_loss=entry - 5, take_profit_1=entry + 5, take_profit_2=entry + 10, ai_confidence=conf,
                 signal_hash=f"h{_next[0]}", created_at=NOW - timedelta(minutes=age_min)))
    s.commit()
    return _next[0]


def test_one_decision_many_rows_one_push_per_user():
    s = _db(users=3)
    ids = [_row(s, user_id=i) for i in (1, 2, 3, 1, 2)]                       # القرار نفسه 5 صفوف، وهي علة البلاغ
    assert B.broadcast_cycle(s, NOW) == 3
    assert sorted(e for e, _ in PUSHES) == ["e1", "e2", "e3"]
    assert s.query(Notification).count() == 3                                  # وجرس التطبيق بلا تكرار أيضاً
    assert all(x.push_broadcast_sent for x in s.query(Signal).filter(Signal.id.in_(ids)).all())


def test_late_row_of_same_decision_in_next_cycle_is_silent():
    s = _db(users=2)
    _row(s)
    B.broadcast_cycle(s, NOW)
    PUSHES.clear()
    late = _row(s, user_id=2)
    assert B.broadcast_cycle(s, NOW + timedelta(minutes=2)) == 0 and PUSHES == []
    assert s.query(Signal).get(late).push_broadcast_sent is True               # لا يُعاد فحصها كل دورة


def test_different_decisions_each_notify():
    s = _db(users=1)
    _row(s, entry=4160.5)
    _row(s, entry=4170.5)                                                      # سعر دخول آخر
    _row(s, entry=4160.5, tf="4h")                                             # فريم آخر
    _row(s, entry=4160.5, side=SignalType.SELL)                                # اتجاه آخر
    _row(s, market="BTCUSD", entry=4160.5)                                     # سوق آخر
    assert B.broadcast_cycle(s, NOW) == 5


def test_same_decision_after_window_notifies_again():
    s = _db(users=1)
    _row(s)
    B.broadcast_cycle(s, NOW)
    s.query(Notification).update({"created_at": NOW - timedelta(hours=B.REPEAT_WINDOW_HOURS + 1)})
    s.commit()
    PUSHES.clear()
    _row(s)
    assert B.broadcast_cycle(s, NOW) == 1


def test_user_watchlist_filter_still_applies():
    s = _db(users=2)
    u2 = s.query(User).get(2)
    u2.notify_watchlist = ["BTCUSD"]
    s.commit()
    _row(s)
    assert B.broadcast_cycle(s, NOW) == 1 and PUSHES[0][0] == "e1"             # تخصيص كل مستخدم كما كان


def test_old_signal_not_pushed_but_marked():
    s = _db(users=1)
    i = _row(s, age_min=B.MAX_SIGNAL_AGE_MIN + 1)
    assert B.broadcast_cycle(s, NOW) == 0
    assert s.query(Signal).get(i).push_broadcast_sent is True


def test_tag_is_same_across_rows_and_used_in_payload():
    s = _db(users=1)
    a, b = _row(s), _row(s, user_id=2)
    A, Bb = s.query(Signal).get(a), s.query(Signal).get(b)
    assert B.decision_tag(A) == B.decision_tag(Bb)
    B.broadcast_cycle(s, NOW)
    assert B.decision_tag(A) in PUSHES[0][1]                                   # sw.js يستبدل بنفس الوسم بدل التكديس


if __name__ == "__main__":
    tests = [(n, f) for n, f in list(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for n, f in tests:
        try:
            f()
            print(f"✅ {n}")
        except Exception as e:
            failed += 1
            import traceback
            print(f"❌ {n}: {type(e).__name__}: {e}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} نجح")
    sys.exit(1 if failed else 0)
