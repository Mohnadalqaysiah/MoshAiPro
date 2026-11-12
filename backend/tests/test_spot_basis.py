"""
تحويل مستويات المعادن من العقد الآجل إلى الفوري (2026-11-12، إشارة #10330): كانت تخرج بأسعار الآجل حين يفشل yfinance .info (404)
أو يُستعمل التقدير النظري (قِيس 25.8$ والفعلي ~2$). الآن: مرجع الآجل من شموع المحرك، ولا تحويل بالتقدير، والصمام يمنع الإشارة.

  cd backend && python tests/test_spot_basis.py      (أو pytest)
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@127.0.0.1:1/x")

from app.services.ai_engine_v5 import mosh_ai_engine_v5 as E  # noqa: E402


def _analysis(fut_ref=3960.0):
    # بيع بمستويات الآجل كما في #10330
    return {"recommendation": "SELL", "current_price": 3958.0, "_futures_ref_price": fut_ref,
            "levels": {"entry": 3960.335, "stop_loss": 3969.61, "tp1": 3951.06, "tp2": 3937.15, "ladder_tp3": 3919.09},
            "entry_zones": [3960.335], "take_profit_zones": [3951.06, 3937.15]}


def _with_spot(value, source, fn):
    orig = E._fetch_spot_price
    E._fetch_spot_price = lambda symbol: (value, source)
    try:
        return fn()
    finally:
        E._fetch_spot_price = orig


def test_shift_uses_engine_candles_not_flaky_info():
    a = _with_spot(3930.0, "tv_spot", lambda: E._apply_spot_basis("XAUUSD", _analysis()))
    assert a.get("spot_basis_applied") is True and a["futures_basis"] == -30.0
    lv = a["levels"]
    assert (lv["entry"], lv["stop_loss"], lv["tp1"], lv["ladder_tp3"]) == (3930.335, 3939.61, 3921.06, 3889.09)
    assert a["current_price"] == 3930.0 and a["price_source"] == "tv_spot"


def test_rejected_shadow_levels_shift_too_and_unconverted_are_skipped():
    a = _analysis()
    a["_pre_reject_levels"] = {"entry": 3960.0, "stop_loss": 3970.0, "tp1": 3950.0}
    a = _with_spot(3930.0, "tv_spot", lambda: E._apply_spot_basis("XAUUSD", a))
    assert a["_pre_reject_levels"] == {"entry": 3930.0, "stop_loss": 3940.0, "tp1": 3920.0}
    bot_src = (ROOT / "app" / "api" / "bot.py").read_text(encoding="utf-8")
    assert "and not _metal_unconverted" in bot_src                                 # الظل المرفوض للمعدن غير المحوّل لا يُسجَّل


def test_theoretical_estimate_is_not_trusted():
    a = _with_spot(3934.0, "theoretical_carry", lambda: E._apply_spot_basis("XAUUSD", _analysis()))
    assert not a.get("spot_basis_applied") and a["levels"]["entry"] == 3960.335       # لم تُزح بتقدير خاطئ


def test_negligible_basis_counts_as_converted():
    a = _with_spot(3959.9, "tv_spot", lambda: E._apply_spot_basis("XAUUSD", _analysis()))
    assert a.get("spot_basis_applied") is True                                      # الفارق 0.1$: الفوري عملياً


def test_absurd_basis_not_applied():
    a = _with_spot(3700.0, "tv_spot", lambda: E._apply_spot_basis("XAUUSD", _analysis()))   # 6.6% — مرجع خاطئ
    assert not a.get("spot_basis_applied")


def test_valve_rejects_unconverted_metal_signal():
    a = E._reject_unconverted_metal("XAUUSD", _analysis())
    assert a["recommendation"] == "WAIT" and a["levels"] == {} and a["take_profit_zones"] == []
    assert a["rejection_reason"].startswith("SPOT_BASIS_UNAVAILABLE")
    import ast
    import re
    bot_src = (ROOT / "app" / "api" / "bot.py").read_text(encoding="utf-8")
    learn = ast.literal_eval(re.search(r"_LEARN_REJECTIONS = (\(.*?\))", bot_src).group(1))
    assert not a["rejection_reason"].startswith(learn)                             # ليس قاعدة تعلّم: لا ظل


def test_valve_is_wired_after_conversion_for_metals_only():
    src = (ROOT / "app" / "services" / "ai_engine_v5.py").read_text(encoding="utf-8")
    i = src.index("analysis = self._apply_spot_basis(symbol, analysis)")
    j = src.index("self._reject_unconverted_metal(symbol, analysis)")
    k = src.index("[PRICE SOURCE]")
    assert i < j < k
    gate = src[src.rindex("if symbol.upper() in self._FUTURES_SPOT_SYMBOLS", 0, j):j]
    assert 'not analysis.get("spot_basis_applied")' in gate and '("BUY", "SELL")' in gate
    assert '_futures_ref = analysis.get("current_price")' in src                     # المرجع قبل استبداله بالحي
    assert E._apply_spot_basis("EURUSD", {"x": 1}) == {"x": 1}                       # غير المعادن لا تُمس


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
