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
import diag_gate as DG  # noqa: E402
from app.database import Base  # noqa: E402
from app.models.market_config import MarketConfig  # noqa: E402
from app.models.signal import Signal, SignalStatus, SignalType  # noqa: E402
from app.models.site_settings import SiteSettings  # noqa: E402
from app.services.weekly_markets import GROUPS, closed_decisions, week_grade, weekly_table  # noqa: E402

NOW = datetime.now(timezone.utc)


def _db(enabled=None):
    TR._cache.clear()
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


def _counting_closed(calls):
    import app.services.weekly_markets as WM
    real = WM.closed_decisions

    def fake(db, since):
        calls.append(since)
        return real(db, since)
    WM.closed_decisions = fake
    return lambda: setattr(WM, "closed_decisions", real)


def test_public_summary_and_trades_are_cached():
    s = _db(True)
    calls = []
    restore = _counting_closed(calls)
    try:
        first = TR.public_summary(weeks=8, db=s)
        n = len(calls)
        assert n and TR.public_summary(weeks=8, db=s) == first and len(calls) == n
        TR.public_trades(weeks=8, group=None, result=None, page=1, page_size=20, db=s)
        n = len(calls)
        t = TR.public_trades(weeks=8, group="forex", result="loss", page=1, page_size=20, db=s)
        assert len(calls) == n and [x["id"] for x in t["items"]] == [2]       # الفلتر يعمل على القائمة المخزَّنة
        TR.public_summary(weeks=4, db=s)
        assert len(calls) > n                                                  # كل نافذة مفتاحها
    finally:
        restore()


def test_filters_do_not_change_cached_order():
    s = _db(True)
    decs = sorted(closed_decisions(s, TR._since(8)), key=lambda d: d["created_at"])   # من الأقدم: عكس ترتيب العرض
    TR._cache_put(("decisions", 8), decs)
    before = [d["id"] for d in decs]
    t = TR.public_trades(weeks=8, group=None, result=None, page=1, page_size=20, db=s)
    assert [x["id"] for x in t["items"]] == before[::-1]                       # العرض من الأحدث
    assert [d["id"] for d in TR._cache[("decisions", 8)][1]] == before         # والمخزَّنة لم تُمس


def test_cache_expires():
    s = _db(True)
    calls = []
    restore = _counting_closed(calls)
    try:
        TR.public_summary(weeks=8, db=s)
        n = len(calls)
        key = ("summary", 8)
        TR._cache[key] = (TR._cache[key][0] - TR.CACHE_TTL - 1, TR._cache[key][1])
        TR.public_summary(weeks=8, db=s)
        assert len(calls) > n
    finally:
        restore()


def test_closing_page_applies_at_once_despite_cache():
    s = _db(True)
    TR.public_summary(weeks=8, db=s)
    TR.public_trades(weeks=8, group=None, result=None, page=1, page_size=20, db=s)
    s.query(SiteSettings).filter(SiteSettings.key == TR.FLAG).update({"value": "false"})
    s.commit()
    for fn in (lambda: TR.public_summary(weeks=8, db=s),
               lambda: TR.public_trades(weeks=8, group=None, result=None, page=1, page_size=20, db=s),
               lambda: asyncio.run(TR.public_chart(1, db=s))):
        try:
            fn()
            assert False, "يجب أن يكون مغلقاً"
        except HTTPException as e:
            assert e.status_code == 404


def test_chart_cached_only_when_ok():
    s = _db(True)
    calls = []

    async def fake(db, signal_id):
        calls.append(signal_id)
        if signal_id == 99:
            raise HTTPException(404, "x")
        return {"ok": True, "id": signal_id}
    real, TR.build_chart_public = TR.build_chart_public, fake
    try:
        for _ in range(2):
            assert asyncio.run(TR.public_chart(1, db=s))["id"] == 1
        assert calls == [1]
        for _ in range(2):
            try:
                asyncio.run(TR.public_chart(99, db=s))
                assert False
            except HTTPException:
                pass
        assert calls == [1, 99, 99]
    finally:
        TR.build_chart_public = real


def test_cache_is_bounded():
    TR._cache.clear()
    for i in range(TR.CACHE_MAX + 5):
        TR._cache_put(("chart", i), {"ok": True})
    assert len(TR._cache) <= TR.CACHE_MAX
    TR._cache.clear()


def _cells(n=100, be=0, r=40.0, won=5):
    """أسبوع بـwon مجموعات رابحة والباقي خاسر."""
    cells = {"_total": {"n": n, "be": be, "r": r}}
    for i, (k, _) in enumerate(GROUPS):
        cells[k] = {"r": 1.0 if i < won else -1.0}
    return cells


def _week(cells, current=False):
    return {"cells": cells, "current": current}


def test_excellent_week_thresholds():
    assert week_grade(_cells())["excellent"] is True                           # الحدّان نفسهما ناجحان: ≥ +0.40R و≥ 5
    assert week_grade(_cells(r=39.9))["excellent"] is False
    assert week_grade(_cells(won=4))["excellent"] is False
    assert week_grade({})["excellent"] is False and week_grade({})["avg_r"] is None


def test_excellent_week_counts_breakeven_in_average():
    g = week_grade(_cells(n=90, be=20, r=41.0))                                # 41 ÷ 110 = +0.37R، ولو حُسب على 90 لنجح
    assert g["n"] == 110 and round(g["avg_r"], 2) == 0.37 and g["excellent"] is False


def test_excellent_week_group_needs_positive_r():
    c = {"_total": {"n": 100, "be": 0, "r": 60.0}}
    c.update({k: {"r": 2.0} for k, _ in GROUPS[:4]})
    c[GROUPS[4][0]] = {"r": 0.0}                                               # متعادلة، والباقي بلا صفقات، و_total لا يُعدّ
    g = week_grade(c)
    assert g["groups_won"] == 4 and g["excellent"] is False


def test_gate_verdict_uses_last_two_complete_weeks():
    good, bad = _week(_cells()), _week(_cells(r=10.0))
    assert DG.verdict([bad, good, good]) is True                               # الأقدم لا يدخل
    assert DG.verdict([good, bad, good]) is False
    assert DG.verdict([good, good, _week(_cells(r=-50.0), current=True)]) is True   # الجاري لا يدخل الحكم
    assert DG.verdict([bad, good, _week(_cells(), current=True)]) is False     # ولا يُكمل أسبوعاً ناقصاً
    assert DG.verdict([good, _week(_cells(), current=True)]) is None


def test_gate_preliminary_verdict_counts_running_week():
    good, bad = _week(_cells()), _week(_cells(r=10.0))
    assert DG.verdict([bad, good, _week(_cells(), current=True)], with_current=True) is True
    assert DG.verdict([bad, good, _week(_cells(r=10.0), current=True)], with_current=True) is False   # العتبات نفسها
    assert DG.verdict([_week(_cells(), current=True)], with_current=True) is None


def _week_of(d):
    return {"from": (d - timedelta(days=d.weekday())).date().isoformat()}


def test_gate_reads_real_table_and_open_trades():
    s = _db(False)
    assert sum(week_grade(w["cells"])["n"] for w in weekly_table(s, weeks=2)["weeks"]) == 4   # الأربع المغلقة والتأمين ضمنها
    assert DG.open_decisions(s, _week_of(NOW - timedelta(days=1))) == 1        # ACTIVE وحدها، من _db
    assert DG.open_decisions(s, _week_of(NOW - timedelta(days=30))) == 0       # أسبوع آخر


def test_gate_open_trades_count_decisions_not_user_rows():
    s = _db(False)
    a = s.query(Signal).filter(Signal.id == 5).one()
    s.add(Signal(id=6, user_id=2, market=a.market, timeframe=a.timeframe, signal_type=a.signal_type, status=a.status,
                 entry_price=a.entry_price, stop_loss=a.stop_loss, take_profit_1=a.take_profit_1,
                 take_profit_2=a.take_profit_2, ai_confidence=70, signal_hash="h6", created_at=a.created_at))
    s.commit()
    assert DG.open_decisions(s, _week_of(a.created_at)) == 1


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
