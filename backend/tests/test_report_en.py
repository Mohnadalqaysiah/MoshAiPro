"""
تقرير الأداء اليومي بالإنجليزية (2026-10-24): نفس الأرقام، بلا حرف عربي، والعربية دون تغيير.

  cd backend && python tests/test_report_en.py      (أو pytest)
"""
import os
import re
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

import app.api.admin as A  # noqa: E402
from app.database import Base  # noqa: E402
from app.models.signal import Signal, SignalStatus, SignalType  # noqa: E402
from app.models.signal_delivery import SignalDelivery  # noqa: E402

AR = re.compile(r"[\u0600-\u06FF]")
NOW = datetime.now(timezone.utc)


def _data():
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng, tables=[Signal.__table__, SignalDelivery.__table__])
    s = sessionmaker(bind=eng)()
    for i, (m, st) in enumerate([("XAUUSD", SignalStatus.TP2_HIT), ("EURUSD", SignalStatus.SL_HIT),
                                 ("BTCUSD", SignalStatus.TP1_HIT)], start=1):
        s.add(Signal(id=i, user_id=1, market=m, timeframe="1h", signal_type=SignalType.BUY, status=st,
                     entry_price=100.0 * i, stop_loss=100.0 * i - 1, take_profit_1=100.0 * i + 1,
                     take_profit_2=100.0 * i + 3, ai_confidence=70, signal_hash=f"h{i}", current_price=100.0 * i,
                     created_at=NOW - timedelta(hours=10), exit_executed=NOW - timedelta(hours=2)))
    s.commit()
    return s, s.query(Signal).all()


def test_report_english():
    db, sigs = _data()
    en, _ = A._build_performance_report(sigs, 1, db, lang="en")
    assert not AR.search(en), en
    for x in ("performance report", "net result", "2 wins", "1 losses", "By market", "XAUUSD", "Top trades", "Losses: 1"):
        assert x in en, x
    ar, _ = A._build_performance_report(sigs, 1, db)
    assert "تقرير أداء Qaffel AI" in ar and "حسب السوق" in ar


if __name__ == "__main__":
    test_report_english()
    print("✓ test_report_english\n1/1 passed")
