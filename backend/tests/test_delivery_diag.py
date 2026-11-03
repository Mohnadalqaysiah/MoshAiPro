"""
اختبارات أداة "لماذا لم تصل الإشارة" (2026-11-03) — الأسباب بنفس ترتيب فلاتر البث.

  cd backend && python tests/test_delivery_diag.py      (أو pytest)
"""
import os
import sys
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@127.0.0.1:1/x")

import diag_delivery as D  # noqa: E402

SIG = NS(market="XAUUSD", timeframe="1h", ai_confidence=72)


def _u(**kw):
    base = dict(id=1, telegram_id="111", is_active=True, plan="MONTHLY", notifications_enabled=True,
                notify_watchlist=["XAUUSD"], notify_timeframes=[], notify_min_confidence=0)
    base.update(kw)
    return NS(**base)


def test_delivered_full_and_masked_and_failed():
    assert D.reasons(_u(), SIG, {1: (True, "full", None)}, set(), False) == ["✅ وصلته (كاملة)"]
    assert D.reasons(_u(), SIG, {1: (True, "masked", None)}, set(), False) == ["✅ وصلته (مموّهة)"]
    assert D.reasons(_u(), SIG, {1: (False, "full", "Forbidden: bot was blocked")}, set(), False)[0].startswith("❌")


def test_each_filter_names_its_reason():
    assert "غير مربوط" in D.reasons(_u(telegram_id=None), SIG, {}, set(), False)[0]
    assert "أطفأ" in D.reasons(_u(notifications_enabled=False), SIG, {}, set(), False)[0]
    assert "ليس ضمن أسواقه" in D.reasons(_u(notify_watchlist=["BTCUSD"]), SIG, {}, set(), False)[0]
    assert "فريمات 15m, 4h" in D.reasons(_u(notify_timeframes=["15m", "4h"]), SIG, {}, set(), False)[0]
    assert "حد الثقة عنده 80%" in D.reasons(_u(notify_min_confidence=80), SIG, {}, set(), False)[0]
    assert "تنبيه مراقبة شخصية" in D.reasons(_u(), SIG, {}, {1}, False)[0]
    assert "حظر البوت" in D.reasons(_u(), SIG, {}, set(), True)[0]
    assert "موقوف" in D.reasons(_u(plan=NS(value="BANNED")), SIG, {}, set(), False)[0]


def test_filters_that_match_do_not_appear():
    r = D.reasons(_u(notify_watchlist=[], notify_timeframes=["all", "1h"], notify_min_confidence=70), SIG, {}, set(), False)
    assert len(r) == 1 and "لا سبب من الفلاتر" in r[0]                       # بلا تخصيص يستلم الكل، 1h مختار، 70 ≤ 72


def test_1day_alias_matches_bot():
    assert "فريمات" not in " ".join(D.reasons(_u(notify_timeframes=["1day"]), NS(market="XAUUSD", timeframe="1d", ai_confidence=72),
                                             {}, set(), False))


def test_owner_who_was_delivered_shows_delivery_not_exclusion():
    assert D.reasons(_u(), SIG, {1: (True, "full", None)}, {1}, False) == ["✅ وصلته (كاملة)"]


def test_merge_deliveries_success_from_any_row_wins():
    rows = [NS(user_id=1, ok=False, variant="full", error="x"), NS(user_id=1, ok=True, variant="masked", error=None),
            NS(user_id=2, ok=False, variant="full", error="blocked"), NS(user_id=None, ok=True, variant="full", error=None)]
    m = D.merge_deliveries(rows)
    assert m == {1: (True, "masked", None), 2: (False, "full", "blocked")}


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
