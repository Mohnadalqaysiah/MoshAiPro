"""
اختبارات "صفقاتي" وشارت التحقق (2026-10-24).

  cd backend && python tests/test_my_trades.py      (أو pytest)
"""
import asyncio
import os
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

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

import app.api.signals as S  # noqa: E402
from app.database import Base  # noqa: E402
from app.models.signal import Signal, SignalStatus, SignalType  # noqa: E402
from app.models.signal_delivery import SignalDelivery  # noqa: E402
from app.services import trade_chart as TC  # noqa: E402

NOW = datetime.now(timezone.utc)


def _db():
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng, tables=[Signal.__table__, SignalDelivery.__table__])
    return sessionmaker(bind=eng)()


def _sig(s, i, user_id, status, entry=100.0, side=SignalType.BUY, hours_ago=10, market="EURUSD"):
    s.add(Signal(id=i, user_id=user_id, market=market, timeframe="1h", signal_type=side, status=status,
                 entry_price=entry, stop_loss=entry - 1, take_profit_1=entry + 1, take_profit_2=entry + 2,
                 ai_confidence=70, signal_hash=f"h{i}", created_at=NOW - timedelta(hours=hours_ago)))


def _deliver(s, sid, user_id, variant="full", ok=True):
    s.add(SignalDelivery(signal_id=sid, user_id=user_id, telegram_id="777", variant=variant, ok=ok))


def _call(s, **kw):
    return S.my_trades(user=SimpleNamespace(id=2), db=s, **{"status": "all", "date_from": None, "date_to": None,
                                                           "page": 1, "page_size": 20, **kw})


def test_includes_own_and_delivered_once_per_decision():
    s = _db()
    _sig(s, 1, 99, SignalStatus.TP1_HIT)                    # وصلته بالبث
    _sig(s, 2, 2, SignalStatus.TP1_HIT, hours_ago=9)        # نفس القرار بصف آخر (مستخدم آخر/نسخته) ← قرار واحد
    _sig(s, 3, 2, SignalStatus.SL_HIT, entry=200)           # تحليله الخاص
    _sig(s, 4, 99, SignalStatus.TP2_HIT, entry=300)         # لم يصله ← لا يظهر
    _deliver(s, 1, 2)
    _deliver(s, 4, 3)
    s.commit()
    r = _call(s)
    assert r["count"] == 2 and {x["id"] for x in r["items"]} == {1, 3}
    assert r["summary"]["wins"] == 1 and r["summary"]["losses"] == 1 and r["summary"]["total_r"] == 0.0


def test_failed_delivery_not_counted_and_masked_open_hidden():
    s = _db()
    _sig(s, 1, 99, SignalStatus.TP1_HIT)
    _sig(s, 2, 99, SignalStatus.ACTIVE, entry=150)
    _sig(s, 3, 99, SignalStatus.SL_HIT, entry=250)
    _deliver(s, 1, 2, ok=False)                             # فشل الإرسال ← لم يصله
    _deliver(s, 2, 2, variant="masked")                     # مفتوحة وصلته مموّهة ← لا تُكشف مستوياتها
    _deliver(s, 3, 2, variant="masked")                     # مغلقة وصلته مموّهة ← تظهر (المغلقة مكشوفة لكل مسجّل)
    s.commit()
    r = _call(s)
    assert [x["id"] for x in r["items"]] == [3] and r["items"][0]["received"] == "masked"


def test_filters_and_pagination():
    s = _db()
    for i, st in enumerate([SignalStatus.TP1_HIT, SignalStatus.SL_HIT, SignalStatus.ACTIVE, SignalStatus.BREAKEVEN], start=1):
        _sig(s, i, 2, st, entry=100 * i, hours_ago=i)
    s.commit()
    assert [x["status"] for x in _call(s, status="win")["items"]] == ["TP1_HIT"]
    assert [x["status"] for x in _call(s, status="open")["items"]] == ["ACTIVE"]
    p = _call(s, page_size=3)
    assert p["pages"] == 2 and len(p["items"]) == 3 and p["items"][0]["id"] == 1       # الأحدث أولاً
    assert _call(s, status="loss")["summary"]["total"] == 4                              # الملخص على كل الفترة


def test_chart_interval_and_window():
    assert TC.pick_interval(NOW - timedelta(hours=10), NOW)[0] == "5m"
    assert TC.pick_interval(NOW - timedelta(days=10), NOW)[0] == "1h"
    assert TC.pick_interval(NOW - timedelta(days=60), NOW)[0] == "1d"
    c = [{"t": NOW - timedelta(hours=h)} for h in range(100, 0, -1)]
    w = TC.window(c, NOW - timedelta(hours=50), NOW - timedelta(hours=40), "1h", before=5, after=3)
    assert len(w) == 5 + 11 + 3


def test_build_chart_closed_only_and_uses_fetch():
    sig = SimpleNamespace(id=7, market="XAUUSD", timeframe="1h", signal_type=SimpleNamespace(value="SELL"),
                          status=SimpleNamespace(value="ACTIVE"), created_at=NOW - timedelta(hours=5),
                          exit_executed=None, expires_at=None, entry_price=4150, stop_loss=4160,
                          take_profit_1=4140, take_profit_2=4140)
    assert asyncio.run(TC.build_chart(sig))["error"] == "الشارت متاح بعد إغلاق الصفقة"
    sig.status, sig.exit_executed = SimpleNamespace(value="TP1_HIT"), NOW - timedelta(hours=2)
    calls = []

    async def fake_fetch(market, interval, bars):
        calls.append((market, interval))
        return [{"t": NOW - timedelta(minutes=5 * k), "o": 1, "h": 2, "l": 0.5, "c": 1.5} for k in range(400, 0, -1)], "src"
    orig, TC._fetch = TC._fetch, fake_fetch
    try:
        r = asyncio.run(TC.build_chart(sig))
    finally:
        TC._fetch = orig
    assert r["ok"] and calls == [("XAUUSD", "5m")] and r["tp2"] is None and r["side"] == "SELL"
    assert r["candles"] and r["candles"][0]["t"] < r["opened_at"]                    # هامش قبل الفتح


def test_routes_order_my_trades_before_signal_id():
    paths = [r.path for r in S.router.routes]
    assert paths.index("/my-trades") < paths.index("/{signal_id}")


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
