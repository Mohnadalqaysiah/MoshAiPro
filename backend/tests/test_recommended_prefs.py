"""
"الإعداد الموصى به" (2026-11-12) ← باقات التخصص (2026-11-14) — recommended_prefs: الباقة الحالية، الانحراف، التطبيق، وأرقام كل باقة.

  cd backend && python tests/test_recommended_prefs.py      (أو pytest)
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import recommended_prefs as R  # noqa: E402

SYMS = {"metals": ["COPPER", "XAGUSD", "XAUUSD"], "crypto": ["BTCUSD", "ETHUSD"], "all": []}


def _user(**kw):
    base = dict(notify_watchlist=[], notify_timeframes=[], notify_min_confidence=0, notifications_enabled=True)
    base.update(kw)
    return SimpleNamespace(**base)


def test_current_preset_by_markets():
    assert R.current_preset(_user(), SYMS) == "all"
    assert R.current_preset(_user(notify_watchlist=None), SYMS) == "all"
    assert R.current_preset(_user(notify_watchlist=["xauusd", "XAGUSD", "COPPER"]), SYMS) == "metals"
    assert R.current_preset(_user(notify_watchlist=["XAUUSD"]), SYMS) == "custom"


def test_deviations_ignore_markets():
    assert R.deviations(_user(notify_watchlist=["XAUUSD"])) == []                 # الأسواق اختيار لا انحراف
    assert R.deviations(_user(notify_timeframes=["all"], notify_min_confidence=None)) == []
    u = _user(notify_timeframes=["1h"], notify_min_confidence=65, notifications_enabled=False)
    assert R.deviations(u) == ["timeframes", "confidence", "notifications"]


def test_apply_sets_markets_and_clears_filters():
    u = _user(notify_watchlist=["EURUSD"], notify_timeframes=["1h"], notify_min_confidence=70, notifications_enabled=False)
    R.apply(u, SYMS["metals"])
    assert R.current_preset(u, SYMS) == "metals" and R.deviations(u) == []
    u.notify_watchlist.append("X")                                                # نسخة لا مرجع
    assert SYMS["metals"] == ["COPPER", "XAGUSD", "XAUUSD"]
    R.apply(u, SYMS["all"])
    assert u.notify_watchlist == [] and R.current_preset(u, SYMS) == "all"


def test_stats_per_preset():
    t0 = datetime(2026, 11, 2, 8, tzinfo=timezone.utc)
    d = lambda h, g, r: {"created_at": t0 + timedelta(hours=h), "group": g, "r": r}
    decs = [d(0, "gold", 1.0), d(1, "metals", -1.0), d(2, "crypto", 2.0), d(24, "gold", 1.0), d(25, "forex", -1.0)]
    st = R.compute_stats(decs, SYMS, days=2)
    assert st["metals"]["n"] == 3 and st["metals"]["per_day"] == 1.5 and st["metals"]["win"] == 67
    assert st["metals"]["pos_days"] == 50 and st["metals"]["symbols"] == 3         # اليوم 1 = 0R: ليس يوماً رابحاً
    assert st["crypto"]["n"] == 1 and st["all"]["n"] == 5 and st["all"]["symbols"] == 0
    assert R.compute_stats([], SYMS, days=2)["metals"] is None
    assert R.RECOMMENDED_PRESET in R.PRESET_KEYS


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
