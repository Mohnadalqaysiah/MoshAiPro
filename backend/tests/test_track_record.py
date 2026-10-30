"""
اختبارات سجل الأداء العام (2026-10-24) — مغلق افتراضياً، كل الصفقات (لا انتقاء)، ومعاينة الأدمن.

  cd backend && python tests/test_track_record.py      (أو pytest)
"""
import asyncio
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

from fastapi import HTTPException  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import app.api.track_record as TR  # noqa: E402
from app.database import Base  # noqa: E402
from app.models.market_config import MarketConfig  # noqa: E402
from app.models.signal import Signal, SignalStatus, SignalType  # noqa: E402
from app.models.site_settings import SiteSettings  # noqa: E402

NOW = datetime.now(timezone.utc)


def _db(enabled=None):
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng, tables=[Signal.__table__, SiteSettings.__table__, MarketConfig.__table__])
    s = sessionmaker(bind=eng)()
    if enabled is not None:
        s.add(SiteSettings(key=TR.FLAG, value="true" if enabled else "false"))
    rows = [(1, "XAUUSD", SignalStatus.TP1_HIT, 2), (2, "EURUSD", SignalStatus.SL_HIT, 3),
            (3, "BTCUSD", SignalStatus.TP2_HIT, 4), (4, "EURUSD", SignalStatus.BREAKEVEN, 5),
            (5, "EURUSD", SignalStatus.ACTIVE, 1)]                           # المفتوحة لا تدخل السجل
    for i, m, st, d in rows:
        s.add(Signal(id=i, user_id=1, market=m, timeframe="1h", signal_type=SignalType.BUY, status=st,
                     entry_price=100.0 * i, stop_loss=100.0 * i - 1, take_profit_1=100.0 * i + 1,
                     take_profit_2=100.0 * i + 2, ai_confidence=70, signal_hash=f"h{i}", current_price=100.0 * i,
                     created_at=NOW - timedelta(days=d), exit_executed=NOW - timedelta(days=d) + timedelta(hours=3)))
    s.commit()
    return s


def test_closed_by_default_and_when_false():
    for s in (_db(None), _db(False)):
        for fn in (lambda: TR.public_summary(db=s), lambda: TR.public_trades(db=s)):
            try:
                fn()
                assert False, "يجب أن يكون مغلقاً"
            except HTTPException as e:
                assert e.status_code == 404


def test_open_shows_all_wins_losses_breakeven_no_cherry_picking():
    s = _db(True)
    sm = TR.public_summary(weeks=8, db=s)
    assert (sm["decisions"], sm["wins"], sm["losses"], sm["breakeven"]) == (4, 2, 1, 1)
    assert sm["total_r"] == round(1 + 2 - 1, 2) and sm["win_rate"] == round(100 * 2 / 3, 1)
    assert sm["avg_r"] == round(sm["total_r"] / sm["decisions"], 3)      # مشتق من الرقمين المعروضين، والتأمين ضمنهما
    t = TR.public_trades(weeks=8, group=None, result=None, page=1, page_size=20, db=s)
    assert t["count"] == 4 and {x["status"] for x in t["items"]} == {"TP1_HIT", "SL_HIT", "TP2_HIT", "BREAKEVEN"}
    assert [x["id"] for x in TR.public_trades(weeks=8, group=None, result="loss", page=1, page_size=20, db=s)["items"]] == [2]
    assert t["items"][0]["tp1"] is not None                                    # المستويات كاملة للتحقق


def test_admin_preview_works_while_closed():
    s = _db(False)
    sm = TR.admin_summary(weeks=8, admin=None, db=s)
    assert sm["enabled"] is False and sm["decisions"] == 4


def test_chart_rejects_pre_baseline_and_open():
    s = _db(True)
    old = Signal(id=9, user_id=1, market="EURUSD", timeframe="1h", signal_type=SignalType.BUY, status=SignalStatus.TP1_HIT,
                 entry_price=1, stop_loss=0.9, take_profit_1=1.1, take_profit_2=1.2, ai_confidence=70, signal_hash="h9",
                 created_at=datetime(2026, 9, 1, tzinfo=timezone.utc))
    s.add(old)
    s.commit()
    for sid, code in ((9, 404), (99, 404), (5, 400)):                          # قبل الخط الأساسي، غير موجودة، مفتوحة
        try:
            asyncio.run(TR.public_chart(sid, db=s))
            assert False
        except HTTPException as e:
            assert e.status_code == code, (sid, e.status_code)


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
