"""
إيقاف صامت للأسهم الأمريكية (2026-11-11، قرار المالك) — الظل بدل العملاء، والخليجية لا تتأثر، وقاعدة الإعادة (12).

  cd backend && python tests/test_us_stocks_pause.py      (أو pytest)
"""
import os
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
from app.services import market_pause as MP  # noqa: E402


def _db():
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng, tables=[User.__table__, Signal.__table__, ShadowSignal.__table__, MarketConfig.__table__])
    s = sessionmaker(bind=eng)()
    s.add(User(id=1, email="a@x.com", password_hash="x", telegram_id="111"))
    s.add(MarketConfig(symbol="COIN", display_name="Coinbase", category="stock"))     # سهم أمريكي أُضيف لاحقاً
    s.add(MarketConfig(symbol="ARAMCO", display_name="Aramco", category="gulf"))
    s.commit()
    MP._cache.update(at=0.0, symbols=set())
    return s


def _save(s, symbol, tf="1h", entry=100.0):
    o_open, o_weekend = B._smart_data.is_market_open, WP.is_weekend
    B._smart_data.is_market_open = lambda sym: True
    WP.is_weekend = lambda now=None: False
    try:
        return B.bot_save_alert_signal(telegram_id="111", symbol=symbol, timeframe=tf, signal_type="BUY",
                                       entry=entry, sl=entry * 0.99, tp1=entry * 1.01, tp2=entry * 1.025, confidence=70,
                                       rr=2.5, tp3=None, wyckoff_phase=None, premium_discount=None, killzone=None,
                                       relaxed_rule=None, db=s)
    finally:
        B._smart_data.is_market_open, WP.is_weekend = o_open, o_weekend


def test_us_stocks_go_to_shadow_by_category():
    os.environ.pop("PAUSE_US_STOCKS", None)
    s = _db()
    for sym in ("AMD", "NFLX", "COIN", "aapl"):
        assert _save(s, sym) == {"saved": False, "reason": "us_stocks_pause"}, sym
    assert s.query(Signal).count() == 0
    assert {r.reason for r in s.query(ShadowSignal).all()} == {"US_STOCKS_PAUSE"}
    assert {r.market for r in s.query(ShadowSignal).all()} >= {"AMD", "NFLX", "COIN"}


def test_other_markets_untouched():
    os.environ.pop("PAUSE_US_STOCKS", None)
    s = _db()
    assert _save(s, "ARAMCO", entry=27.0)["saved"] is True                    # الخليجية فئة مستقلة
    assert _save(s, "XAUUSD", entry=4000.0)["saved"] is True
    assert s.query(ShadowSignal).count() == 0


def test_kill_switch():
    s = _db()
    try:
        os.environ["PAUSE_US_STOCKS"] = "0"
        assert MP.stocks_paused(s, "AMD") is False
        assert _save(s, "AMD")["saved"] is True
    finally:
        os.environ.pop("PAUSE_US_STOCKS", None)


def test_all_save_paths_and_rule_12():
    for path in ("app/api/bot.py", "app/api/signals.py"):
        src = (ROOT / path).read_text(encoding="utf-8")
        i = src.index("elif stocks_paused(db, symbol):")
        assert src.index("elif coin_trial(symbol):") < i < src.index("elif tf_paused(symbol, timeframe):", i), path
    assert W.rule_stocks_restore([0.5] * 19)[0] == "waiting"
    assert W.rule_stocks_restore([0.1] * 20)[0] == "candidate"
    assert W.rule_stocks_restore([0.05] * 20)[0] == "ok"


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
