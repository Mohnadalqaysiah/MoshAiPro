"""
اختبار رد "التحليل الذكي" بالإنجليزية (2026-10-24): نفس الأرقام، بلا حرف عربي.

  cd backend && python tests/test_chat_en.py      (أو pytest)
"""
import os
import re
import sys
import types
from pathlib import Path

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

from app.services.chat_agent import trading_agent as A  # noqa: E402

AR = re.compile(r"[؀-ۿ]")
ANALYSIS = {
    "current_price": 80586.95, "recommendation": "BUY", "ai_confidence_score": 72.0, "market_open": True,
    "entry_zones": [80397.59], "stop_loss_zone": 80169.92, "take_profit_zones": [80927.66, 81932.14], "risk_reward_ratio": 2.4,
    "market_structure": {"trend": "BULLISH", "structure": "HH_HL"},
    "premium_discount": {"zone": "DISCOUNT", "pct": 44.3, "ote_level": 80885.53, "equilibrium": 80556.27},
    "kill_zone": {"active_session": "London", "is_optimal_time": True},
    "order_blocks": {"bullish_obs": [{"low": 80455.41, "high": 81335.83}], "bearish_obs": []},
    "fvg": {"bullish_fvgs": [{"low": 80187.89, "high": 80376.95}], "bearish_fvgs": []},
    "liquidity": {"nearest_ssl": 80377.81, "nearest_bsl": 81932.14},
    "confluence": {"factors": ["FVG صاعد قريب جداً (0.14%)"]},          # عربي من المحرك — لا يُعرض بالإنجليزية
    "gemini_analysis": {"enabled": True, "arabic_summary": "ملخص عربي"},
}


def test_english_reply_no_arabic_same_numbers():
    r = A._build_direct_response(ANALYSIS, "BTCUSD", "1h", lang="en")
    m = r["message"]
    assert not AR.search(m), m
    for x in ("80586.95", "80397.59", "80169.92", "80927.66", "81932.14", "1:2.4", "72.0%", "BUY", "Trade levels"):
        assert x in m, x


def test_wait_and_error_paths_english():
    w = A._build_direct_response({**ANALYSIS, "recommendation": "WAIT"}, "BTCUSD", "1h", lang="en")["message"]
    assert not AR.search(w) and "What are we waiting for?" in w
    e = A._build_direct_response({"error": "timeout"}, "BTCUSD", "1h", lang="en")["message"]
    assert not AR.search(e) and "Couldn't fetch BTCUSD" in e


def test_arabic_unchanged_by_default():
    m = A._build_direct_response(ANALYSIS, "BTCUSD", "1h")["message"]
    assert "مستويات التداول" in m and "عوامل التأكيد" in m


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
