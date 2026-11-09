"""
عملات الكريبتو الجديدة بالظل (2026-11-09) — السجل الموحّد، وتوجيه الإشارة للظل لا للعملاء، وقاعدة المراقبة (11).

  cd backend && python tests/test_new_coins.py      (أو pytest)
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
from app.services import crypto_registry as CR  # noqa: E402
from app.services import market_scanner as MS  # noqa: E402
from app.services import smart_data as SD  # noqa: E402
from app.services import spread_table as SPT  # noqa: E402
from app.services import tv_price_feed as TV  # noqa: E402

NEW = ["AVAXUSD", "LINKUSD", "LTCUSD", "BCHUSD", "DOTUSD", "SUIUSD"]


def test_registry_trial_and_kill_switch():
    os.environ.pop("NEW_COIN_TRIAL", None)
    assert CR.symbols("trial") == NEW and CR.trial_symbols() == NEW
    assert all(CR.is_trial(s) for s in NEW) and CR.is_trial("AVAX/USD")
    assert not any(CR.is_trial(s) for s in ("BTCUSD", "DOGEUSD", "XAUUSD", "", None))
    try:
        os.environ["NEW_COIN_TRIAL"] = "0"
        assert CR.trial_symbols() == [] and not CR.is_trial("AVAXUSD")
    finally:
        os.environ.pop("NEW_COIN_TRIAL", None)


def test_data_sources_wired_without_touching_live_coins():
    for s in NEW:
        assert SD.YFINANCE_MAP[s] == CR.COINS[s][4]
        assert TV.TV_SYMBOL_MAP[s] == CR.COINS[s][3]
        assert SPT.TYPICAL_SPREAD[s] == CR.COINS[s][5]
        assert SD.smart_data.is_market_open(s) is True                       # كريبتو 24/7
        assert s in MS.SCAN_SYMBOLS
    assert SD.smart_data.is_market_open("DOGEUSD") is True                   # كانت تُعامل كفوركس
    for s in ("XRPUSD", "ADAUSD", "DOGEUSD"):
        assert s not in TV.TV_SYMBOL_MAP                                       # مصدر العملات الحية لم يتغير
    assert SD.YFINANCE_MAP["BTCUSD"] == "BTC-USD" and SPT.TYPICAL_SPREAD["BTCUSD"] == 15.0


def _db():
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng, tables=[User.__table__, Signal.__table__, ShadowSignal.__table__, MarketConfig.__table__])
    s = sessionmaker(bind=eng)()
    s.add(User(id=1, email="a@x.com", password_hash="x", telegram_id="111"))
    s.commit()
    return s


def _save(s, symbol, tf, entry, weekend=False):
    o_open, o_weekend = B._smart_data.is_market_open, WP.is_weekend
    B._smart_data.is_market_open = lambda sym: True
    WP.is_weekend = lambda now=None: weekend
    WP._cache.update(at=0.0, symbols=set())
    try:
        return B.bot_save_alert_signal(telegram_id="111", symbol=symbol, timeframe=tf, signal_type="BUY",
                                       entry=entry, sl=entry * 0.99, tp1=entry * 1.01, tp2=entry * 1.025, confidence=70,
                                       rr=2.5, tp3=None, wyckoff_phase=None, premium_discount=None, killzone=None,
                                       relaxed_rule=None, db=s)
    finally:
        B._smart_data.is_market_open, WP.is_weekend = o_open, o_weekend


def test_trial_coin_signal_goes_to_shadow_not_clients():
    os.environ.pop("NEW_COIN_TRIAL", None)
    s = _db()
    assert _save(s, "AVAXUSD", "1h", 8.5) == {"saved": False, "reason": "new_coin_trial"}
    assert s.query(Signal).count() == 0
    sh = s.query(ShadowSignal).one()
    assert (sh.reason, sh.market, sh.timeframe, sh.source) == ("NEW_COIN_TRIAL", "AVAXUSD", "1h", "watch")
    assert _save(s, "BTCUSD", "1h", 70000.0)["saved"] is True                  # الحية كما هي


def test_trial_coin_respects_weekend_pause():
    s = _db()
    assert _save(s, "LINKUSD", "1h", 10.6, weekend=True)["reason"] == "crypto_weekend_pause"   # بلا صف MarketConfig
    assert s.query(ShadowSignal).one().reason in (None, "crypto_weekend")


def test_all_three_save_paths_route_trial_before_15m():
    for path, marker in (("app/api/bot.py", "elif coin_trial(symbol):"), ("app/api/signals.py", "elif coin_trial(symbol):")):
        src = (ROOT / path).read_text(encoding="utf-8")
        assert src.count(marker) == 1, path
        assert src.index(marker) < src.index("elif tf_paused(symbol, timeframe):", src.index(marker) - 2000), path
    bot = (ROOT / "app/api/bot.py").read_text(encoding="utf-8")
    assert '"reason": "new_coin_trial"' in bot


def test_rule_11_thresholds():
    up, live = [0.5] * 10, [0.4] * 20
    assert W.rule_new_coin([0.5] * 9, live)[0] == "waiting"
    assert W.rule_new_coin(up, live)[0] == "candidate"
    assert W.rule_new_coin([-0.1] * 10, live)[0] == "reject"
    assert W.rule_new_coin([0.15] * 10, live)[0] == "extend"                   # ≥ +0.1R لكن < نصف الحي (0.2)
    assert W.rule_new_coin([0.15] * 10, [])[0] == "candidate"                  # بلا حي للمقارنة: شرط +0.1R وحده


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
