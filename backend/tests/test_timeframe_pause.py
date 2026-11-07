"""
اختبارات إيقاف 15m عدا الذهب والمعادن (2026-11-07) — مسار تنبيه المراقبة الحقيقي على قاعدة بيانات، وقاعدتا الإعادة والاستثناء.

  cd backend && python tests/test_timeframe_pause.py      (أو pytest)
"""
import os
import sys
import types
from datetime import datetime, timedelta, timezone
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

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import app.api.bot as B  # noqa: E402
import app.services.weekend_policy as WP  # noqa: E402
import diag_watch as W  # noqa: E402
from app.database import Base  # noqa: E402
from app.models.market_config import MarketConfig  # noqa: E402
from app.models.shadow_signal import ShadowSignal  # noqa: E402
from app.models.signal import Signal  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services import timeframe_pause as P  # noqa: E402


def test_which_markets_are_paused():
    os.environ.pop("PAUSE_15M", None)
    for s in ("BTCUSD", "ETHUSD", "EURUSD", "USDJPY", "NAS100", "US30", "USOIL", "NATGAS", "AAPL", "ARAMCO"):
        assert P.tf_paused(s, "15m") is True, s
    for s in ("XAUUSD", "XAU/USD", "XAGUSD", "XPTUSD", "XPDUSD", "COPPER"):
        assert P.tf_paused(s, "15m") is False, s                                # الاستثناء: الذهب والمعادن
    for tf in ("1h", "4h", "5m", "30m"):
        assert P.tf_paused("BTCUSD", tf) is False                              # 15m وحده
    assert P.tf_paused("", "15m") is False


def test_kill_switch():
    try:
        for v in ("0", "false", "off", "No"):
            os.environ["PAUSE_15M"] = v
            assert P.tf_paused("BTCUSD", "15m") is False
        os.environ["PAUSE_15M"] = "1"
        assert P.tf_paused("BTCUSD", "15m") is True
    finally:
        os.environ.pop("PAUSE_15M", None)


def _db():
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng, tables=[User.__table__, Signal.__table__, ShadowSignal.__table__, MarketConfig.__table__])
    s = sessionmaker(bind=eng)()
    s.add(User(id=1, email="a@x.com", password_hash="x", telegram_id="111"))
    s.commit()
    return s


def _save(s, symbol, tf, entry):
    return B.bot_save_alert_signal(telegram_id="111", symbol=symbol, timeframe=tf, signal_type="BUY",
                                   entry=entry, sl=entry * 0.99, tp1=entry * 1.01, tp2=entry * 1.025, confidence=70, rr=2.5,
                                   tp3=None, wyckoff_phase=None, premium_discount=None, killzone=None, relaxed_rule=None, db=s)


def _patched(fn):
    o_open, o_weekend = B._smart_data.is_market_open, WP.is_weekend
    B._smart_data.is_market_open = lambda sym: True
    WP.is_weekend = lambda now=None: False                                     # فحص العطلة لا يتدخل بيوم الاختبار
    try:
        return fn()
    finally:
        B._smart_data.is_market_open, WP.is_weekend = o_open, o_weekend


def test_watch_alert_on_paused_market_goes_to_shadow_not_signals():
    os.environ.pop("PAUSE_15M", None)
    s = _db()
    r = _patched(lambda: _save(s, "BTCUSD", "15m", 70000.0))
    assert r == {"saved": False, "reason": "tf15m_pause"}                      # البوت لا يرسل التنبيه حين saved=False
    assert s.query(Signal).count() == 0
    sh = s.query(ShadowSignal).one()
    assert (sh.reason, sh.market, sh.timeframe, sh.source) == ("TF15M_PAUSE", "BTCUSD", "15m", "watch")


def test_watch_alert_on_exempt_or_other_timeframe_is_saved():
    os.environ.pop("PAUSE_15M", None)
    s = _db()
    assert _patched(lambda: _save(s, "XAUUSD", "15m", 4000.0))["saved"] is True     # ذهب 15m يعمل
    assert _patched(lambda: _save(s, "BTCUSD", "1h", 70000.0))["saved"] is True     # كريبتو 1h يعمل
    assert s.query(Signal).count() == 2 and s.query(ShadowSignal).count() == 0


def test_weekend_pause_still_wins_for_crypto():
    s = _db()
    o_open, o_weekend = B._smart_data.is_market_open, WP.is_weekend
    B._smart_data.is_market_open = lambda sym: True
    WP.is_weekend = lambda now=None: True
    try:
        r = _save(s, "BTCUSD", "15m", 70000.0)
    finally:
        B._smart_data.is_market_open, WP.is_weekend = o_open, o_weekend
    assert r["reason"] == "crypto_weekend_pause"                               # قياس كريبتو العطلة كما كان
    assert s.query(ShadowSignal).one().reason == "crypto_weekend"


def test_every_signal_creation_path_checks_the_pause_first():
    """الماسح وتحليل البوت (bot_analyze) والموقع (signals.analyze_market) تُنشئ صف Signal أيضاً: الفحص قبل الإنشاء بكل مسار."""
    import inspect
    import app.api.signals as S
    for fn in (B.bot_analyze, S.analyze_market, B.bot_save_alert_signal):
        src = inspect.getsource(fn)
        assert "tf_paused(symbol, timeframe)" in src and "reason=TF_PAUSE_REASON" in src, fn.__name__
        assert src.index("tf_paused(symbol, timeframe)") < src.index("Signal("), fn.__name__


def test_restore_rule():
    assert W.rule_restore([0.5] * 39, [0.4] * 10)[0] == "waiting"
    assert W.rule_restore([0.3] * 40, [0.5] * 10)[0] == "candidate"            # ≥ +0.1 و≥ نصف 1h
    assert W.rule_restore([0.2] * 40, [0.5] * 10)[0] == "ok"                   # أقل من نصف 1h
    assert W.rule_restore([0.05] * 40, [0.0] * 10)[0] == "ok"                  # أقل من +0.1
    assert W.rule_restore([0.3] * 40, [])[0] == "waiting"


def test_exception_watch_uses_rule_2_thresholds():
    assert W.rule_15m([-0.1] * 29, [0.5] * 10, need=30)[0] == "waiting"
    assert W.rule_15m([0.05] * 30, [0.5] * 10, need=30)[0] == "candidate"
    assert W.rule_15m([0.4] * 30, [0.5] * 10, need=30)[0] == "ok"


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
