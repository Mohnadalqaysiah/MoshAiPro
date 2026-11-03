"""
اختبارات القياس الصامت لإصلاح FVG بالمحرك (2026-11-03) — لا يتغير قرار ولا ذاكرة، ويُسجَّل كل فرق بنوعه.

  cd backend && python tests/test_fvg_shadow.py      (أو pytest)
"""
import copy
import os
import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd

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

from app.services.ai_engine_v5 import mosh_ai_engine_v5 as ENGINE  # noqa: E402
from app.services.ict_engine import ict_engine  # noqa: E402
from app.services.smart_data import smart_data  # noqa: E402


def _df(seed=7, n=150):
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 0.6, n))
    high = close + rng.uniform(0.1, 0.8, n)
    low = close - rng.uniform(0.1, 0.8, n)
    openp = np.r_[close[0], close[:-1]]
    df = pd.DataFrame({"datetime": pd.date_range("2026-10-01", periods=n, freq="h", tz="UTC"),
                       "open": openp, "high": np.maximum(high, openp), "low": np.minimum(low, openp),
                       "close": close, "volume": 1000.0})
    return smart_data._add_indicators(df)


def _analysis(seed=7):
    df = _df(seed)
    a = ict_engine.full_analysis(df, "EURUSD", "1h")
    return a, df


def test_no_base_when_old_flag_and_fixed_flag_agree():
    a, df = _analysis()
    a["fvg"]["in_bullish_fvg"] = a["fvg"]["in_bearish_fvg"] = False
    a["fvg"]["inside"] = {"bullish": False, "bearish": False}
    assert ENGINE._fvg_shadow_base(a, df) is None                                # لا فرق ممكن، لا عمل إضافي


def test_base_recomputes_confluence_without_touching_real_analysis():
    a, df = _analysis()
    a["fvg"]["inside"] = {"bullish": True, "bearish": False}
    before = copy.deepcopy(a)
    base = ENGINE._fvg_shadow_base(a, df)
    assert a == before                                                           # الحقيقي لم يُمس
    assert base["fvg"]["in_bullish_fvg"] is True and base["fvg"]["in_bearish_fvg"] is False
    assert base["confluence"]["bull_score"] == a["confluence"]["bull_score"] + 15 - \
        (8 if a["fvg"].get("bullish_fvgs") and a["fvg"]["bullish_fvgs"][0]["distance_pct"] < 0.5 else 0)
    assert base["recommendation"] == base["confluence"]["direction"]


def test_decide_runs_real_layers_without_engine_state_changes():
    for seed in (1, 7, 21, 42):
        a, df = _analysis(seed)
        a["fvg"]["inside"] = {"bullish": not a["fvg"]["in_bullish_fvg"], "bearish": False}
        base = ENGINE._fvg_shadow_base(a, df)
        state = (copy.deepcopy(ENGINE._last_signal_issued), copy.deepcopy(ENGINE._signal_history),
                 copy.deepcopy(getattr(ENGINE, "_last_signal_time", {})))
        real = copy.deepcopy(a)
        cf = ENGINE._fvg_shadow_decide(base, real, "EURUSD", "1h", None, "4h", None)
        assert cf["recommendation"] in ("BUY", "SELL", "WAIT", "NO TRADE", "NO_TRADE")
        assert (ENGINE._last_signal_issued, ENGINE._signal_history, getattr(ENGINE, "_last_signal_time", {})) == state


def _run(real_rec, cf_rec, basis=None, symbol="EURUSD"):
    recorded = []
    real = {"recommendation": real_rec, "futures_basis": basis, "levels": {"entry": 100, "stop_loss": 99, "tp1": 101, "tp2": 103}}
    snap = copy.deepcopy(real)
    o_decide, o_rec = ENGINE._fvg_shadow_decide, ENGINE._fvg_shadow_record
    ENGINE._fvg_shadow_decide = lambda *a, **k: {"recommendation": cf_rec,
                                                 "levels": {"entry": 200, "stop_loss": 198, "tp1": 202, "tp2": 205}}
    ENGINE._fvg_shadow_record = lambda kind, a, side, sym, tf, b: recorded.append((kind, side, a["levels"]["entry"], b))
    try:
        out = ENGINE._fvg_shadow_run({}, real, real_rec, symbol, "1h", None, "4h", None)
    finally:
        ENGINE._fvg_shadow_decide, ENGINE._fvg_shadow_record = o_decide, o_rec
    assert real == snap
    return out, recorded


def test_run_records_each_kind_of_difference():
    assert _run("BUY", "BUY") == (None, [])
    assert _run("WAIT", "WAIT") == (None, [])
    assert _run("WAIT", "SELL", basis=-12.0) == ("NEW", [("NEW", "SELL", 200, -12.0)])          # مستويات النسخة + فارق الآجل
    assert _run("BUY", "WAIT") == ("DROP", [("DROP", "BUY", 100, None)])                        # مستويات الحي كما هي
    assert _run("BUY", "SELL") == ("NEW+DROP", [("NEW", "SELL", 200, None), ("DROP", "BUY", 100, None)])


def test_run_never_raises_and_always_reenables_logs():
    from loguru import logger
    seen = []
    sink = logger.add(lambda m: seen.append(m), level="INFO", filter="app.services.ai_engine_v5")
    o = ENGINE._fvg_shadow_decide
    ENGINE._fvg_shadow_decide = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    try:
        assert ENGINE._fvg_shadow_run({}, {"recommendation": "BUY"}, "BUY", "EURUSD", "1h", None, "4h", None) is None
    finally:
        ENGINE._fvg_shadow_decide = o
    logger.remove(sink)
    assert any("FVG shadow skipped" in str(m) for m in seen)                     # يُكتب من المحرك بعد إعادة التفعيل: السجل عاد يعمل


def test_record_shifts_only_futures_and_uses_far_target():
    import app.services.weekend_policy as W
    import app.database as Dd
    calls = []
    o_rs, o_sl = W.record_shadow, Dd.SessionLocal
    W.record_shadow = lambda db, **k: calls.append(k)
    Dd.SessionLocal = lambda: types.SimpleNamespace(close=lambda: None)
    lv = {"levels": {"entry": 4000.0, "stop_loss": 3990.0, "tp1": 4010.0, "tp2": 4025.0, "ladder_tp3": 4060.0}, "ai_confidence_score": 70}
    try:
        ENGINE._fvg_shadow_record("NEW", lv, "BUY", "XAUUSD", "1h", -12.0)
        ENGINE._fvg_shadow_record("NEW", lv, "BUY", "EURUSD", "1h", -12.0)
    finally:
        W.record_shadow, Dd.SessionLocal = o_rs, o_sl
    assert (calls[0]["entry"], calls[0]["tp2"], calls[0]["reason"]) == (3988.0, 4048.0, "FVG_FIX_NEW")
    assert (calls[1]["entry"], calls[1]["tp2"]) == (4000.0, 4060.0)               # لا فارق آجل لغير المعادن


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
