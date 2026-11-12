"""
"الإعداد الموصى به" (2026-11-12) — recommended_prefs: كشف الانحراف والتطبيق باتفاقية البث (فارغة = الكل، 0 = كل النسب).

  cd backend && python tests/test_recommended_prefs.py      (أو pytest)
"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import recommended_prefs as R  # noqa: E402


def _user(**kw):
    base = dict(notify_watchlist=[], notify_timeframes=[], notify_min_confidence=0, notifications_enabled=True)
    base.update(kw)
    return SimpleNamespace(**base)


def test_default_user_is_recommended():
    assert R.deviations(_user()) == []
    assert R.deviations(_user(notify_timeframes=["all"], notify_min_confidence=None, notify_watchlist=None)) == []


def test_each_deviation_detected():
    u = _user(notify_watchlist=["XAUUSD"], notify_timeframes=["1h"], notify_min_confidence=65, notifications_enabled=False)
    assert R.deviations(u) == ["watchlist", "timeframes", "confidence", "notifications"]


def test_apply_resets_to_recommended():
    u = _user(notify_watchlist=["XAUUSD", "EURUSD"], notify_timeframes=["1h"], notify_min_confidence=70,
              notifications_enabled=False)
    R.apply(u)
    assert R.deviations(u) == []
    assert u.notify_watchlist == [] and u.notify_timeframes == [] and u.notify_min_confidence == 0 and u.notifications_enabled
    u.notify_watchlist.append("X")                       # نسخة لا مرجع للثابت
    assert R.RECOMMENDED["notify_watchlist"] == []


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
