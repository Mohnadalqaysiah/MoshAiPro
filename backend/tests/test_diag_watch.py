"""
(2026-10-27) قواعد المراقبة الأربع المسجّلة — العتبات حرفياً كما في DECISIONS.md 27/10.

  cd backend && python tests/test_diag_watch.py
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import diag_watch as W  # noqa: E402


def test_simple_rule_thresholds():
    assert W.rule_simple([-1.0] * 14, 15)[0] == "waiting"
    assert W.rule_simple([-1.0] * 15, 15)[0] == "candidate"
    assert W.rule_simple([-1.0] * 6 + [1.0] * 9, 15)[0] == "ok"          # +0.2R
    assert W.rule_simple([-0.3] * 10, 10)[0] == "ok"                      # −0.3 ليس أسوأ من −0.3


def test_15m_rule_needs_both_conditions():
    assert W.rule_15m([0.0] * 39, [1.0])[0] == "waiting"
    assert W.rule_15m([0.05] * 40, [0.5] * 10)[0] == "candidate"          # < نصف 1h و< +0.1
    assert W.rule_15m([0.2] * 40, [1.0] * 10)[0] == "ok"                  # < نصف 1h لكن ≥ +0.1
    assert W.rule_15m([0.05] * 40, [0.08] * 10)[0] == "ok"                # < +0.1 لكن ليس < نصف 1h


def test_iso_weeks_only_completed():
    assert W.iso_weeks(datetime(2026, 11, 1, 23, tzinfo=timezone.utc)) == []
    wk = W.iso_weeks(datetime(2026, 11, 9, 1, tzinfo=timezone.utc))
    assert [a.date().isoformat() for a, _ in wk] == ["2026-10-28", "2026-11-02"]


def test_premium_rule_two_consecutive_positive_weeks():
    now = datetime(2026, 11, 9, 1, tzinfo=timezone.utc)
    w1, w2 = datetime(2026, 10, 29, tzinfo=timezone.utc), datetime(2026, 11, 3, tzinfo=timezone.utc)
    ok = [(w1 + timedelta(hours=i), 0.2) for i in range(10)] + [(w2 + timedelta(hours=i), 0.1) for i in range(10)]
    assert W.rule_premium(ok, now)[0] == "candidate"
    assert W.rule_premium(ok[:-1], now)[0] == "ok"                        # 19 < 20
    neg = ok[:10] + [(w2, -5.0)] + ok[10:]
    assert W.rule_premium(neg, now)[0] == "ok"                            # الأسبوع الثاني سالب
    assert W.rule_premium(ok, datetime(2026, 11, 5, tzinfo=timezone.utc))[0] == "waiting"
    old = [(datetime(2026, 10, 27, tzinfo=timezone.utc), 9.0)]           # قبل البداية لا يُحسب
    assert W.rule_premium(old + ok[:-1], now)[0] == "ok"


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
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
