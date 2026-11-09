"""
اختبارات تفضيلات 15m وهو موقوف، ومواعيد تحذيرات الأخبار (2026-11-09).

  cd backend && python tests/test_15m_prefs_and_news.py      (أو pytest)
"""
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "telegram-bot"))
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@127.0.0.1:1/x")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.database as Dd  # noqa: E402
import econ_calendar as EC  # noqa: E402
import migrate_15m_prefs as MG  # noqa: E402
from app.models.site_settings import SiteSettings  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services import timeframe_pause as P  # noqa: E402

UTC = timezone.utc


def test_nfp_first_friday_with_new_york_time():
    assert EC.nfp_utc(2026, 11) == datetime(2026, 11, 6, 13, 30, tzinfo=UTC)          # شتاءً: 08:30 نيويورك = 13:30
    assert EC.nfp_utc(2026, 7) == datetime(2026, 7, 3, 12, 30, tzinfo=UTC)            # صيفاً = 12:30
    assert EC.first_friday(2026, 5) == date(2026, 5, 1)


def test_news_only_on_real_days_not_every_week():
    fridays = [datetime(2026, 11, 6, 12, 30, tzinfo=UTC) + timedelta(weeks=w) for w in range(4)]
    assert [len(EC.due(f)) for f in fridays] == [1, 0, 0, 0]                           # كان 4 من 4
    assert EC.due(datetime(2026, 11, 10, 11, 30, tzinfo=UTC)) == []                   # ثلاثاء: لا CPI بلا تاريخ
    assert EC.due(datetime(2026, 11, 11, 17, 0, tzinfo=UTC)) == []                    # أربعاء: لا FOMC بلا تاريخ
    assert EC.due(datetime(2026, 11, 6, 13, 0, tzinfo=UTC)) == []                     # بعد نافذة الساعة


def test_dated_extra_events_fire_once_in_window():
    assert [k for k, _ in EC.due(datetime(2026, 11, 10, 12, 30, tzinfo=UTC))] == ["CPI"]   # 08:30 نيويورك − ساعة
    assert EC.due(datetime(2026, 12, 9, 18, 0, tzinfo=UTC))[0][0] == "FOMC"
    assert [k for k, _ in EC.due(datetime(2026, 12, 10, 12, 30, tzinfo=UTC))] == ["CPI"]
    assert EC.due(datetime(2026, 12, 16, 18, 0, tzinfo=UTC)) == []                         # لا تكرار أسبوعي
    assert EC.due(datetime(2026, 11, 17, 12, 30, tzinfo=UTC)) == []


def test_bot_loops_respect_mute_and_use_calendar():
    src = (ROOT.parent / "telegram-bot" / "bot.py").read_text(encoding="utf-8")
    for fn in ("market_session_notifier", "session_pre_alert", "economic_news_alert"):
        body = src[src.index(f"async def {fn}("):]
        body = body[:body.index("\nasync def ", 10)] if "\nasync def " in body[10:] else body
        assert 'notifications_enabled") is False' in body, fn
    news = src[src.index("async def economic_news_alert("):]
    assert "econ_calendar.due(now)" in news and 'now.weekday() != ev["weekday"]' not in news
    assert 'callback_data="wltf_15m"' not in src                                       # زر 15m مخفي وهو موقوف


def test_preferences_drop_15m_while_paused():
    os.environ.pop("PAUSE_15M", None)
    assert P.allowed_pref_timeframes(["15m", "1h"]) == ["1h"]
    assert P.allowed_pref_timeframes(["15m"]) == [] and P.allowed_pref_timeframes(["all"]) == []
    try:
        os.environ["PAUSE_15M"] = "0"
        assert P.allowed_pref_timeframes(["15m", "1h"]) == ["15m", "1h"]               # بعد الإعادة يُقبل
    finally:
        os.environ.pop("PAUSE_15M", None)


def _db():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Dd.Base.metadata.create_all(eng, tables=[User.__table__, SiteSettings.__table__])
    S = sessionmaker(bind=eng)
    s = S()
    s.add_all([User(id=1, email="a@x.com", password_hash="x", notify_timeframes=["15m"], notify_timeframe="15m"),
               User(id=2, email="b@x.com", password_hash="x", notify_timeframes=["15m", "4h"], notify_timeframe="1h"),
               User(id=3, email="c@x.com", password_hash="x", notify_timeframes=["1h"], notify_timeframe="1h"),
               User(id=4, email="d@x.com", password_hash="x", notify_timeframes=[], notify_timeframe="15m")])
    s.commit()
    s.close()
    Dd.SessionLocal = S
    return S


def _run(*args):
    old = sys.argv
    sys.argv = ["x", *args]
    try:
        MG.main()
    finally:
        sys.argv = old


def test_migration_preview_apply_and_restore():
    S = _db()
    _run()                                                                              # معاينة لا تكتب
    s = S()
    assert s.query(User).get(1).notify_timeframes == ["15m"]
    s.close()
    _run("--apply")
    s = S()
    got = {u.id: (u.notify_timeframes, u.notify_timeframe) for u in s.query(User).all()}
    assert got == {1: ([], "1h"), 2: ([], "1h"), 3: (["1h"], "1h"), 4: ([], "1h")}     # كل من اختار 15m = كل الفريمات
    backup = json.loads(s.query(SiteSettings).filter(SiteSettings.key == MG.BACKUP_KEY).one().value)
    assert set(backup) == {"1", "2", "4"} and backup["2"]["timeframes"] == ["15m", "4h"]
    s.query(User).filter(User.id == 4).update({"notify_timeframes": ["4h"]})          # المستخدم 4 غيّر بنفسه
    s.commit()
    s.close()
    _run("--apply")                                                                     # تطبيق ثانٍ لا يكتب فوق النسخة
    s = S()
    assert json.loads(s.query(SiteSettings).filter(SiteSettings.key == MG.BACKUP_KEY).one().value)["1"]["timeframes"] == ["15m"]
    s.close()
    _run("--restore")
    s = S()
    got = {u.id: (u.notify_timeframes, u.notify_timeframe) for u in s.query(User).all()}
    assert got[1] == (["15m"], "15m") and got[2] == (["15m", "4h"], "1h")
    assert got[4] == (["4h"], "1h")                                                    # اختياره الجديد لا يُمحى
    s.close()


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
