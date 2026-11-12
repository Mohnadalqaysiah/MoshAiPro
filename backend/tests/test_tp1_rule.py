"""
قاعدة 0.7R المسجّلة 30/10 — حكم diag_target_profile.rule_07 (2026-11-12): P مقابل O بالمجموع وأغلب الأسابيع ونسبة ربح +5 نقاط.

  cd backend && python tests/test_tp1_rule.py      (أو pytest)
"""
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@127.0.0.1:1/x")

_argv = sys.argv
sys.argv = ["x"]                       # الأداة تقرأ وسائطها عند الاستيراد
import diag_target_profile as T  # noqa: E402
sys.argv = _argv


def _res(profile, week, rs):
    return [(profile, "crypto", (2026, week), date(2026, 11, 2), r) for r in rs]


def test_parse_since():
    assert T._parse_since("2026-10-31") == (datetime(2026, 10, 31, tzinfo=timezone.utc), None)
    assert T._parse_since("21") == (None, 21)
    assert T._parse_since("tests/x.py") == (None, 14)                          # وسيط غريب (pytest) لا يكسر الاستيراد
    assert T.RULE_07_DATE == datetime(2026, 11, 28, tzinfo=timezone.utc)


def test_rule_passes_only_when_all_three_hold():
    o = _res("O", 45, [1.0] * 6 + [-1.0] * 6) + _res("O", 46, [1.0] * 5 + [-1.0] * 7)
    p = _res("P", 45, [0.7] * 8 + [-1.0] * 4) + _res("P", 46, [0.7] * 7 + [-1.0] * 5)
    v = T.rule_07(o + p)
    assert v["c_total"] and v["c_weeks"] and v["c_wr"] and v["pass"]           # 50%/42% ← 67%/58%، المجموع أعلى
    assert (v["weeks"], v["better"]) == (2, 2)


def test_rule_fails_on_total_or_win_rate_or_weeks():
    o = _res("O", 45, [2.5] * 6 + [-1.0] * 6)
    p = _res("P", 45, [0.7] * 8 + [-1.0] * 4)                                 # ربح أعلى لكن مجموع أقل
    v = T.rule_07(o + p)
    assert v["c_wr"] and not v["c_total"] and not v["pass"]
    o = _res("O", 45, [1.0] * 6 + [-1.0] * 6)
    p = _res("P", 45, [1.2] * 6 + [-1.0] * 6)                                 # مجموع أعلى ونسبة نفسها
    v = T.rule_07(o + p)
    assert v["c_total"] and not v["c_wr"] and not v["pass"]
    o = _res("O", 45, [1.0] * 6 + [-1.0] * 6) + _res("O", 46, [1.0] * 6 + [-1.0] * 6) + _res("O", 47, [1.0] * 2 + [-1.0] * 10)
    p = _res("P", 45, [0.7] * 5 + [-1.0] * 7) + _res("P", 46, [0.7] * 5 + [-1.0] * 7) + _res("P", 47, [0.7] * 12)
    v = T.rule_07(o + p)
    assert (v["weeks"], v["better"]) == (3, 1) and not v["c_weeks"] and not v["pass"]   # أسبوع واحد كبير لا يكفي


def test_small_weeks_not_counted_and_missing_profiles():
    o = _res("O", 45, [1.0] * 6 + [-1.0] * 6) + _res("O", 48, [-1.0] * 3)          # الأسبوع الجزئي (3) لا يُعدّ
    p = _res("P", 45, [0.7] * 8 + [-1.0] * 4) + _res("P", 48, [-1.0] * 3)
    assert T.rule_07(o + p)["weeks"] == 1
    assert T.rule_07(o) is None


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
