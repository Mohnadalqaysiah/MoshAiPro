"""
محاكاة الدخول بأمر معلّق مقابل سعر السوق (2026-11-12) — منطق diag_entry_mode.simulate على حالات نعرف جوابها، ومنها #10330.

  cd backend && python tests/test_entry_mode.py      (أو pytest)
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@127.0.0.1:1/x")

import diag_entry_mode as D  # noqa: E402

T0 = datetime(2026, 11, 12, 8, 13, tzinfo=timezone.utc)
NOW = T0 + timedelta(days=3)


def _bars(spec, start=T0 - timedelta(minutes=8)):
    """spec: [(أعلى، أدنى، إغلاق)] كل 5 دقائق."""
    return [(start + timedelta(minutes=5 * i), h, lo, c) for i, (h, lo, c) in enumerate(spec)]


def test_10330_limit_misses_market_wins():
    # بيع: الدخول 3960.33، الوقف 3969.61، الأهداف 3951.06 / 3937.15 / 3919.09؛ السعر عند الإشارة ~3958.5 ثم أقرب 3959.34 ثم هبوط
    rows = _bars([(3963.2, 3958.3, 3958.5), (3959.34, 3954.9, 3955.0), (3956.8, 3950.8, 3951.0), (3951.4, 3945.1, 3946.0),
                  (3940.0, 3925.0, 3930.0), (3922.0, 3910.0, 3912.0)])
    tps = D._targets(3951.06, 3937.15, 3919.09, False)
    end = T0 + timedelta(hours=24)
    assert D.simulate(rows, T0, end, 3960.335, 3969.61, tps, False, "limit", NOW) == (None, "not_triggered")
    r, st = D.simulate(rows, T0, end, 3960.335, 3969.61, tps, False, "market", NOW)
    assert st == "traded" and abs(r - (3958.5 - 3919.09) / (3969.61 - 3958.5)) < 1e-9   # البعيد بمخاطرة الدخول بالسوق


def test_market_skips_late_and_invalid():
    tps = D._targets(101.0, 102.5, None, True)
    end = T0 + timedelta(hours=24)
    late = _bars([(101.5, 101.0, 101.2), (102.0, 100.8, 101.0)])                        # السعر تجاوز الهدف 1 عند الإشارة
    assert D.simulate(late, T0, end, 100.0, 99.0, tps, True, "market", NOW)[1] == "late"
    invalid = _bars([(99.1, 98.5, 98.8), (99.5, 98.0, 99.0)])                           # تجاوز الوقف
    assert D.simulate(invalid, T0, end, 100.0, 99.0, tps, True, "market", NOW)[1] == "invalid"


def test_same_accounting_stop_first_and_highest_target_locks():
    tps = D._targets(101.0, 102.5, None, True)
    end = T0 + timedelta(hours=24)
    after = T0 + timedelta(minutes=2)                                                    # شموع تبدأ بعد الإشارة
    rows = _bars([(100.2, 99.9, 100.0), (101.2, 99.95, 101.1), (101.5, 98.9, 99.0)], after)   # هدف 1 ثم الوقف: يبقى هدف 1
    assert D.simulate(rows, T0, end, 100.0, 99.0, tps, True, "limit", NOW) == (1.0, "traded")
    same_bar = _bars([(100.2, 99.9, 100.0), (101.2, 98.9, 100.0)], after)               # الوقف والهدف بنفس الشمعة: الوقف أولاً
    assert D.simulate(same_bar, T0, end, 100.0, 99.0, tps, True, "limit", NOW) == (-1.0, "traded")
    expiry = _bars([(100.2, 99.9, 100.0), (100.6, 100.1, 100.5)], after)
    r, st = D.simulate(expiry, T0, T0 + timedelta(minutes=10), 100.0, 99.0, tps, True, "limit", NOW)
    assert st == "traded" and abs(r - 0.5) < 1e-9                                        # انتهت بلا هدف: آخر إغلاق
    assert D.simulate(expiry, T0, NOW + timedelta(days=1), 100.0, 99.0, tps, True, "limit", NOW)[1] == "open"


def _res(group, week, rl, rm, sl="traded", sm="traded"):
    return (group.upper(), group, (2026, week), rl, sl, rm, sm)


def test_forward_rule_all_four_needed():
    good = [_res("forex", 47, 0.5, 0.8) for _ in range(16)] + [_res("forex", 48, 0.4, 0.6) for _ in range(16)] + \
           [_res("crypto", 47, 0.5, 0.4) for _ in range(16)]                       # الكريبتو أسوأ: سوق واحد مسموح
    v = D.rule_entry(good)
    assert v["c_total"] and v["c_weeks"] and v["c_groups"] and v["c_avg"] and v["pass"]
    assert v["worse_groups"] == ["crypto"]
    two_worse = good + [_res("metals", 48, 0.9, 0.1) for _ in range(16)]           # سوقان أسوأ ← لا
    assert not D.rule_entry(two_worse)["c_groups"]
    one_week = [_res("forex", 47, 0.2, 0.9) for _ in range(20)] + [_res("forex", 48, 0.5, 0.4) for _ in range(20)]
    assert not D.rule_entry(one_week)["c_weeks"] and not D.rule_entry(one_week)["pass"]   # أسبوع واحد لا يكفي
    assert D.rule_entry([_res("forex", 45, 0.5, 0.8)]) is None                    # خارج W47/W48 لا يُحتسب


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
