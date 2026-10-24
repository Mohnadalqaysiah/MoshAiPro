"""
اختبار واجهة البوت بالإنجليزية (2026-10-24، المرحلة 3): التحليل الفوري، خطوات الرأي، تنبيه الحماية — بلا حرف عربي.

  cd backend && python tests/test_bot_english.py      (أو pytest)
"""
import os
import re
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "telegram-bot"))
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "")


class _Stub(types.ModuleType):
    def __getattr__(self, n):
        if n.startswith("__"):
            raise AttributeError(n)
        return type(n, (), {"__init__": lambda self, *a, **k: None})


for _m in ("telegram", "telegram.ext", "telegram.constants", "telegram.error", "aiohttp"):
    sys.modules.setdefault(_m, _Stub(_m))
sys.modules["telegram.ext"].filters = types.SimpleNamespace(TEXT=1, COMMAND=1, PHOTO=1, VIDEO=1)

import bot as B  # noqa: E402
import review_flow as RF  # noqa: E402

AR = re.compile(r"[؀-ۿ]")
DATA = {"recommendation": "BUY", "ai_confidence_score": 74, "current_price": 2400.5, "trade_type": "SWING",
        "trade_type_label": "🎯 سوينغ", "trade_type_warning": "تحذير عربي",
        "levels": {"entry": 2400.0, "stop_loss": 2390.0, "tp1": 2410.0, "tp2": 2425.0, "risk_reward": 2.5},
        "order_blocks": {"bullish_obs": [{"low": 2395, "high": 2398}], "bearish_obs": []},
        "liquidity": {"nearest_ssl": 2388, "nearest_bsl": 2430},
        "premium_discount": {"zone": "DISCOUNT"}, "wyckoff": {"phase": "ACCUMULATION"}}


def test_quick_analysis_english():
    t = B.fmt_analysis_en(DATA, "XAUUSD", "1h")
    assert not AR.search(t), t
    for x in ("XAUUSD", "BUY", "2,400" if "2,400" in t else "2400", "Stop", "TP1", "TP2", "R/R", "Support OB"):
        assert x in t, x
    w = B.fmt_analysis_en({**DATA, "recommendation": "WAIT"}, "XAUUSD", "1h")
    assert not AR.search(w) and "WAIT (NO TRADE)" in w
    assert "Couldn't analyze" in B.fmt_analysis_en({"error": "x"}, "XAUUSD", "1h")


def test_labels_and_helpers_english():
    assert B.mname("XAUUSD", "en") == "XAUUSD" and B.tf_label("4h", "en") == "4 hours"
    assert not AR.search(B.cat_label("gulf", "en")) and B._t("en", "عربي", "English") == "English"
    assert not AR.search(B.fmt_breakeven({"market": "XAUUSD", "signal_type": "SELL", "timeframe": "1h",
                                          "entry": 2400, "tp1": 2390}, "en"))
    assert not AR.search(B.HELP_EN)


def test_review_flow_english():
    f = RF.ReviewFlow()
    f.start(9, "en")
    texts = [f.on_rating(9, 5), f.on_media(9, "audio", "x")[1], f.on_skip(9), f.on_text(9, "short")[1]]
    ok, consent = f.on_text(9, "Great signals and clear levels every day")
    texts.append(consent)
    texts += [RF.EN["THANKS"], f.cancel(9)]
    for t in texts:
        assert t and not AR.search(t), t
    g = RF.ReviewFlow()
    g.start(1)                                   # الافتراضي عربي كما كان
    assert AR.search(g.on_rating(1, 4))


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
