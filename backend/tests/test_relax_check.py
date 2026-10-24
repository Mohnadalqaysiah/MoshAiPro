"""
اختبارات diag_relax_check.py (2026-10-24) — التفصيل والتركّز والتداخل مع صفقات المنصة، على بيانات مصطنعة معروفة الجواب.

  cd backend && python tests/test_relax_check.py      (أو pytest)
"""
import io
import os
import sys
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@127.0.0.1:1/x")

import diag_relax_check as D  # noqa: E402

T0 = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)   # الاثنين W43


def _sh(market, r, hours=0, side="SELL", tf="1h"):
    return SimpleNamespace(market=market, r_multiple=r, created_at=T0 + timedelta(hours=hours),
                           signal_type=side, timeframe=tf)


def _pf(market, side, start_h, end_h):
    return SimpleNamespace(market=market, signal_type=SimpleNamespace(value=side),
                           created_at=T0 + timedelta(hours=start_h), exit_executed=T0 + timedelta(hours=end_h),
                           expires_at=None)


def test_stats_and_breakdown():
    s = D.stats([1.0, -1.0, 2.0])
    assert s["n"] == 3 and s["w"] == 2 and abs(s["avg"] - 2 / 3) < 1e-9 and s["tot"] == 2.0
    reps = [_sh("XAUUSD", 1), _sh("XAUUSD", 1), _sh("EURUSD", -1)]
    b = dict(D.breakdown(reps, lambda x: x.market))
    assert b["XAUUSD"]["tot"] == 2 and b["EURUSD"]["tot"] == -1
    assert D.breakdown(reps, lambda x: x.market)[0][0] == "XAUUSD"          # مرتبة بالمجموع


def test_concentration_detects_single_source():
    """كل الربح من الذهب ← بدونه سالب: هذا ما يجب أن يكشفه الفحص قبل التخفيف."""
    reps = [_sh("XAUUSD", 2) for _ in range(5)] + [_sh("EURUSD", -1) for _ in range(3)]
    c = D.concentration(reps, lambda x: x.market)
    assert c["top"] == "XAUUSD" and c["top_tot"] == 10 and c["rest_tot"] == -3 and c["rest_n"] == 3
    assert abs(c["share"] - 100 * 10 / 7) < 1e-9


def test_overlap_same_opposite_none():
    platform = [_pf("XAUUSD", "SELL", -2, 5), _pf("EURUSD", "BUY", -2, 5)]
    reps = [_sh("XAUUSD", 1, hours=1),            # منصة تبيع الذهب وقتها ← تكرار
            _sh("EURUSD", 1, hours=1),            # منصة تشتري ← تعارض
            _sh("XAUUSD", 1, hours=10),           # بعد إغلاق صفقة المنصة ← إضافة
            _sh("BTCUSD", 1, hours=1)]            # لا شيء ← إضافة
    ov = D.overlap(reps, platform)
    assert len(ov["same"]) == 1 and len(ov["opposite"]) == 1 and len(ov["none"]) == 2


def test_overlap_window_includes_hour_before_and_falls_back_to_expiry():
    p = SimpleNamespace(market="XAUUSD", signal_type="SELL", created_at=T0, exit_executed=None,
                        expires_at=T0 + timedelta(hours=3))
    ov = D.overlap([_sh("XAUUSD", 1, hours=-0.5), _sh("XAUUSD", 1, hours=2.5), _sh("XAUUSD", 1, hours=4)], [p])
    assert len(ov["same"]) == 2 and len(ov["none"]) == 1


def test_reports_render_without_errors():
    reps = [_sh("XAUUSD", 1.5, hours=h) for h in range(4)] + [_sh("EURUSD", -1, hours=30, tf="15m")]
    buf = io.StringIO()
    with redirect_stdout(buf):
        D.report_reason("ZONE_CONFLICT_SELL_IN_DISCOUNT", reps, reps[:2], [_pf("XAUUSD", "SELL", -1, 1)],
                        lambda m: "commodity" if m == "XAUUSD" else "forex")
        D.report_tp2([{"created_at": T0 - timedelta(days=10), "entry": 100, "stop_loss": 99, "tp2": 110, "r": -1.0},
                      {"created_at": T0, "entry": 100, "stop_loss": 99, "tp2": 103, "r": 1.0}])
    out = buf.getvalue()
    assert "حسب الفئة" in out and "أكبر رمز: XAUUSD" in out and "إضافة حقيقية" in out
    assert "لا صفقات بهدف ≥ 8R بعد 14/10" in out            # الوحيدة ≥8R قبل 14/10


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
