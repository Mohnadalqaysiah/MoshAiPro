"""
تغطية بصمة السوق (2026-11-12): كانت 117 من 659 قراراً و18 من 2496 فرصة ظل فقط — صفوف المراقبة والظل المرفوض بلا بصمة،
والجدولة من مسار متزامن تسقط بصمت. هنا: الجدولة تعمل من المسارين، ولقطة التحليل تمر من analyze-multi-tf إلى صف التنبيه.

  cd backend && python tests/test_fingerprint_coverage.py      (أو pytest)
"""
import asyncio
import os
import sys
import threading
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
from app.database import Base  # noqa: E402
from app.models.market_config import MarketConfig  # noqa: E402
from app.models.shadow_signal import ShadowSignal  # noqa: E402
from app.models.signal import Signal  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services import market_fingerprint as MF  # noqa: E402


def _spy_capture():
    calls, done = [], threading.Event()

    async def fake(snap, symbol, timeframe, signal_type, signal_id, shadow_id):
        calls.append((snap, symbol, timeframe, signal_type, signal_id, shadow_id))
        done.set()

    return calls, done, fake


def test_schedule_works_from_sync_thread_and_from_event_loop():
    calls, done, fake = _spy_capture()
    orig = MF._capture_own_session
    MF._capture_own_session = fake
    try:
        th = MF.schedule(None, "BTCUSD", "1h", "BUY", signal_id=7, snapshot={"confidence": 70, "x": 1, "wyckoff": [1]})
        assert isinstance(th, threading.Thread)                                # بلا حلقة أحداث: خيط مستقل لا إسقاط صامت
        th.join(5)
        assert done.is_set()
        snap = calls[0][0]
        assert snap["confidence"] == 70 and "x" not in snap and snap["wyckoff"] is None   # مفاتيح معروفة وقيم بسيطة فقط

        async def inside_loop():
            t = MF.schedule({"ai_confidence_score": 55}, "ETHUSD", "4h", "SELL", shadow_id=9)
            assert isinstance(t, asyncio.Task)
            await t
        asyncio.run(inside_loop())
        assert calls[-1][0]["confidence"] == 55 and calls[-1][5] == 9
        assert MF.schedule(None, "X", "1h", "BUY") is None                     # بلا معرّف لا شيء
    finally:
        MF._capture_own_session = orig


def _db():
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng, tables=[User.__table__, Signal.__table__, ShadowSignal.__table__, MarketConfig.__table__])
    s = sessionmaker(bind=eng)()
    s.add(User(id=1, email="a@x.com", password_hash="x", telegram_id="111"))
    s.commit()
    return s


def _save(s, **kw):
    o_open, o_weekend = B._smart_data.is_market_open, WP.is_weekend
    B._smart_data.is_market_open = lambda sym: True
    WP.is_weekend = lambda now=None: False
    try:
        return B.bot_save_alert_signal(telegram_id="111", symbol="XAUUSD", timeframe="1h", signal_type="BUY",
                                       entry=4000.0, sl=3990.0, tp1=4010.0, tp2=4025.0, confidence=71, rr=2.5,
                                       tp3=None, wyckoff_phase="markup", premium_discount="discount", killzone=None,
                                       relaxed_rule=None, db=s, **kw)
    finally:
        B._smart_data.is_market_open, WP.is_weekend = o_open, o_weekend


def test_watch_alert_records_fingerprint_with_snapshot_from_bot():
    seen = []
    orig = MF.schedule
    MF.schedule = lambda *a, **k: seen.append((a, k))
    try:
        s = _db()
        res = _save(s, fp={"market_state": "TRENDING", "volatility": "HIGH", "confidence": None, "bad": {"x": 1}})
        assert res["saved"] is True
        (args, kw), = seen
        assert kw["signal_id"] == res["signal_id"] and args[1:4] == ("XAUUSD", "1h", "BUY")
        snap = kw["snapshot"]
        assert snap["market_state"] == "TRENDING" and snap["volatility"] == "HIGH" and "bad" not in snap
        assert snap["confidence"] == 71 and snap["wyckoff"] == "markup" and snap["pd_zone"] == "discount"   # مكمّلة من التنبيه
        seen.clear()
        s2 = _db()
        assert _save(s2)["saved"] is True and seen == []                       # استدعاء مباشر بلا لقطة: لا التقاط
    finally:
        MF.schedule = orig


def test_multi_tf_returns_snapshot_per_timeframe():
    orig = B.mosh_ai_engine_v5.analyze_market_multi_tf

    async def fake(symbol, timeframes):
        return {tf: {"recommendation": "BUY", "ai_confidence_score": 66, "calibration_params": {"market_state": "RANGING"},
                     "levels": {"atr": 2.0, "risk_reward": 2.5}, "current_price": 100.0} for tf in timeframes}
    B.mosh_ai_engine_v5.analyze_market_multi_tf = fake
    try:
        out = asyncio.run(B.bot_analyze_multi_tf(symbol="XAUUSD", timeframes="1h,4h", _=True))
    finally:
        B.mosh_ai_engine_v5.analyze_market_multi_tf = orig
    for tf in ("1h", "4h"):
        fp = out["data"][tf]["_fp"]
        assert fp["market_state"] == "RANGING" and fp["confidence"] == 66 and fp["atr_pct"] == 2.0 and fp["rr"] == 2.5
        assert set(fp) == set(MF.FP_KEYS)


def test_rejected_shadow_and_bot_wiring():
    src = (ROOT / "app" / "api" / "bot.py").read_text(encoding="utf-8")
    i = src.index('_shid = record_shadow(db, source="rejected"')
    assert "market_fingerprint.schedule(analysis, symbol, timeframe, _pre, shadow_id=_shid)" in src[i:i + 1500]
    bot = (ROOT.parent / "telegram-bot" / "bot.py").read_text(encoding="utf-8")
    j = bot.index('"/api/v1/bot/save-alert-signal"')
    assert 'json={"fp": data.get("_fp") or {}}' in bot[j:j + 400]


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
