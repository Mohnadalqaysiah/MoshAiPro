"""
(2026-10-30) أساليب السلّم في diag_target_profile: L و M و O (فكرة هدف ثانٍ عند 2.5R) بالمقارنة مع F و C.

  cd backend && python tests/test_target_ladder.py
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@127.0.0.1:1/x")

import diag_target_profile as P  # noqa: E402

T0 = datetime(2026, 10, 1, tzinfo=timezone.utc)


def play(path, profile, entry=100.0, sl=99.0, tp1=101.0, tp2=106.0, buy=True):
    """path = [(high, low)] شمعة كل 5 دقائق، والإغلاق بمنتصفها."""
    rows = [(T0 + timedelta(minutes=5 * i), hi, lo, (hi + lo) / 2) for i, (hi, lo) in enumerate(path)]
    return P.run(rows, T0, T0 + timedelta(days=1), entry, sl, tp1, tp2, buy, profile)


UP_THEN_BACK = [(100.1, 99.9), (101.2, 100.2), (102.6, 101.1), (101.5, 100.8), (100.5, 99.95)]
ALL_THE_WAY = [(100.1, 99.9), (101.2, 100.2), (102.6, 101.1), (106.2, 102.5)]
REACH_1R_ONLY = [(100.1, 99.9), (101.2, 100.2), (100.5, 99.95)]
STOPPED = [(100.1, 99.9), (100.2, 98.9)]


def near(a, b):
    return abs(a - b) < 1e-9


def test_reversal_after_2_5r():
    assert near(play(UP_THEN_BACK, "L"), (1 + 2.5 + 0) / 3)
    assert near(play(UP_THEN_BACK, "M"), 0.5 + 1.25)
    assert near(play(UP_THEN_BACK, "C"), 0.5)          # اليوم: نصف عند 1R والباقي يعود للدخول
    assert near(play(UP_THEN_BACK, "O"), 2.5)
    assert near(play(UP_THEN_BACK, "F"), 1.0)


def test_full_run_to_far_target():
    assert near(play(ALL_THE_WAY, "L"), (1 + 2.5 + 6) / 3)
    assert near(play(ALL_THE_WAY, "M"), 1.75)          # M يتخلى عن البعيد
    assert near(play(ALL_THE_WAY, "C"), 0.5 + 3.0)
    assert near(play(ALL_THE_WAY, "O"), 6.0)


def test_reaches_only_1r():
    assert near(play(REACH_1R_ONLY, "L"), 1 / 3)
    assert near(play(REACH_1R_ONLY, "M"), 0.5)
    assert near(play(REACH_1R_ONLY, "O"), 1.0)


def test_stop_before_any_target():
    for p in "LMOCFP":
        assert play(STOPPED, p) == -1.0


def test_p_uses_0_7r_first_target():
    touch_07 = [(100.1, 99.9), (100.8, 100.2), (100.3, 98.9)]
    assert near(play(touch_07, "P"), 0.7)               # 0.7R ثم وقف: يُقفل +0.7R
    assert play(touch_07, "O") == -1.0                  # نفس الصفقة بهدف 1R خاسرة
    assert near(play(REACH_1R_ONLY, "P"), 0.7)          # بلغت 1R: تُقفل عند 0.7R فقط
    assert near(play(UP_THEN_BACK, "P"), 2.5)
    assert near(play(ALL_THE_WAY, "P"), 6.0)


def test_sell_side_mirrors_buy():
    mirror = [(200 - lo, 200 - hi) for hi, lo in UP_THEN_BACK]
    assert near(play(mirror, "L", entry=100.0, sl=101.0, tp1=99.0, tp2=94.0, buy=False), (1 + 2.5) / 3)
    assert near(play(mirror, "O", entry=100.0, sl=101.0, tp1=99.0, tp2=94.0, buy=False), 2.5)


def test_near_far_target_stays_two_steps():
    assert near(play(ALL_THE_WAY, "L", tp2=102.0), 0.5 + 1.0)   # البعيد 2R ≤ 2.5R فهدفان فقط
    assert near(play(ALL_THE_WAY, "O", tp2=102.0), 2.0)


def test_expired_entered_helpers():
    import diag_expired_entered as D
    t = lambda h: T0 + timedelta(hours=h)
    data = [(t(1), 0, 0, 10.0), (t(2), 0, 0, 11.0), (t(3), 0, 0, 12.0), (t(4), 0, 0, 13.0)]
    assert D.last_close_before(data, t(2), t(3)) == 12.0
    assert D.last_close_before(data, t(5), t(6)) is None
    assert D.estimate_r(100, 99, 102) == 2.0 and D.estimate_r(100, 101, 102) == -2.0
    assert D.estimate_r(100, 99, None) is None
    s = D.summarize([("W1", 1.0), ("W1", -0.5), ("W0", None)])
    assert list(s) == ["W0", "W1"] and s["W1"][:4] == [2, 2, 1, 1] and s["W0"][:2] == [1, 0]


if __name__ == "__main__":
    tests =[(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for n, f in tests:
        try:
            f()
            print(f"✅ {n}")
        except Exception as e:
            failed += 1
            print(f"❌ {n}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} نجح")
    sys.exit(1 if failed else 0)
