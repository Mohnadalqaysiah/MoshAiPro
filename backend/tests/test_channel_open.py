"""
اختبارات إشارات القناة المفتوحة (2026-10-31) — العدد من إعداد اللوحة، والباقي مموّه، والعدّ يصمد بعد إعادة تشغيل البوت.

  cd backend && python tests/test_channel_open.py      (أو pytest)
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "telegram-bot"))
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@127.0.0.1:1/x")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import messages as M  # noqa: E402
from app.database import Base  # noqa: E402
from app.models.site_settings import SiteSettings  # noqa: E402
from app.services import channel_open as C  # noqa: E402

T = datetime(2026, 10, 31, 8, 0, tzinfo=timezone.utc)
SIG = {"signal_type": "BUY", "market": "XAUUSD", "entry_price": 4160.5, "stop_loss": 4150.5, "take_profit_1": 4170.5, "take_profit_2": 4185.5}


def _db(limit=None):
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng, tables=[SiteSettings.__table__])
    s = sessionmaker(bind=eng)()
    if limit is not None:
        s.add(SiteSettings(key=C.LIMIT_KEY, value=str(limit)))
        s.commit()
    return s


def test_default_is_all_masked():
    assert C.claim(_db(None), T) is False                                      # بلا إعداد: لا تغيير عن اليوم
    assert C.claim(_db(0), T) is False
    assert C.claim(_db("abc"), T) is False                                     # قيمة خاطئة لا تفتح إشارات
    assert C.claim(_db(-2), T) is False


def test_exact_count_opens_then_masked():
    s = _db(2)
    assert [C.claim(s, T + timedelta(hours=i)) for i in range(4)] == [True, True, False, False]


def test_new_day_resets_count():
    s = _db(1)
    assert C.claim(s, T) is True and C.claim(s, T) is False
    assert C.claim(s, T + timedelta(days=1)) is True


def test_count_survives_bot_restart():
    s = _db(1)
    assert C.claim(s, T) is True
    s2 = sessionmaker(bind=s.get_bind())()                                     # جلسة جديدة، والبوت لا يحفظ العدد
    assert C.claim(s2, T) is False


def test_owner_raising_limit_mid_day_applies():
    s = _db(1)
    C.claim(s, T)
    s.query(SiteSettings).filter(SiteSettings.key == C.LIMIT_KEY).update({"value": "2"})
    s.commit()
    assert C.claim(s, T) is True and C.claim(s, T) is False


def test_channel_text_open_has_levels_masked_hides_them():
    full = M.signal_full(SIG, "الذهب", "ساعة", 75)
    masked = M.signal_masked(SIG, "الذهب", "ساعة")
    opened, hidden = M.channel_text(masked, full, True), M.channel_text(masked, full, False)
    assert "4,150.5" in opened or "4150.5" in opened                           # الوقف ظاهر
    assert "4150.5" not in hidden and "4,150.5" not in hidden
    assert "شراء" not in hidden                                                # المموّهة بلا اتجاه
    assert M.DISCLAIMER in opened                                              # المفتوحة تبقى بإخلاء المسؤولية
    assert M.CHANNEL_LINE not in opened and M.CHANNEL_LINE not in hidden       # لا "تابع قناتنا" داخل القناة


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
