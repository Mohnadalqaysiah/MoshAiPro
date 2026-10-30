"""
اختبارات سلّم الأهداف الثلاثة (2026-10-30) — tp_ladder، المحرك، وحلقة الرصد الحقيقية bot_check_outcomes على قاعدة بيانات.

  cd backend && python tests/test_tp_ladder.py      (أو pytest)

المهم هنا: لا تتغير قواعد الرصد القديمة (لمس الدخول بالضبط، الوقف أولاً، الهدف المقفل يبقى)، ولا تتأثر صفقات الهدفين.
"""
import asyncio
import os
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@127.0.0.1:1/x")
os.environ["TP_LADDER_ENABLED"] = "1"


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
from app.database import Base  # noqa: E402
from app.models.signal import Signal, SignalStatus, SignalType  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services import tp_ladder as L  # noqa: E402
from app.services.ai_engine_v5 import mosh_ai_engine_v5 as ENGINE  # noqa: E402
from app.services.quality_report import _r_multiple  # noqa: E402

NOW = datetime.now(timezone.utc)
MKT = "ADAUSD"          # خارج TradingView: السعر والشموع من _smart_data المستبدل
ENTRY, SL, TP1, TP2, TP3 = 100.0, 99.0, 101.0, 102.5, 106.0


class FakeData:
    """شموع 5m تبدأ قبل إنشاء الإشارة (المشي يغطي عمرها) ثم مسار الاختبار."""

    def __init__(self):
        self.path, self.price = [], 100.0

    def is_market_open(self, _):
        return True

    def get_realtime_price_with_meta(self, _):
        return {"price": self.price}

    async def get_ohlcv(self, sym, tf, bars=30):
        t0 = datetime.now(timezone.utc) - timedelta(hours=2)
        rows = [{"datetime": t0, "high": 100.05, "low": 99.95}]        # أقدم من الإنشاء: لا تُفحص
        for i, (hi, lo) in enumerate(self.path):
            rows.append({"datetime": datetime.now(timezone.utc) - timedelta(minutes=60 - 5 * i), "high": hi, "low": lo})
        return pd.DataFrame(rows)


class FakeEngine:
    def __init__(self):
        self.calls = []

    def update_performance(self, r):
        self.calls.append(r)

    def get_winrate(self):
        return 0.5


def _db():
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng, tables=[Signal.__table__, User.__table__])
    db = sessionmaker(bind=eng)()
    db.add(User(id=9, email="a@b.c", telegram_id="77", is_active=True, language="ar"))
    db.commit()
    return db


def _sig(db, i=1, status=SignalStatus.ACTIVE, tp3=TP3, entered=False, side=SignalType.BUY, market=MKT,
         entry=ENTRY, sl=SL, tp1=TP1, tp2=TP2, expires_h=24):
    s = Signal(id=i, user_id=9, market=market, timeframe="1h", signal_type=side, status=status, entry_price=entry,
               stop_loss=sl, take_profit_1=tp1, take_profit_2=tp2, take_profit_3=tp3, ai_confidence=70,
               signal_hash=f"h{i}", created_at=NOW - timedelta(minutes=90), expires_at=NOW + timedelta(hours=expires_h),
               broadcast_sent=False, entry_executed=(NOW - timedelta(minutes=85)) if entered else None)
    db.add(s)
    db.commit()
    return s


def _cycle(db, data, path, range_check=True, price=None):
    data.path = path
    if price is not None:
        data.price = price
    return asyncio.run(B.bot_check_outcomes(range_check=range_check, _=True, db=db))


class _Env:
    """يستبدل مصادر البيانات والمحرك داخل وحدة الحلقة ويعيدها بعد الاختبار."""

    def __enter__(self):
        self.data, self.engine = FakeData(), FakeEngine()
        self.saved = (B._smart_data, B.mosh_ai_engine_v5)
        B._smart_data, B.mosh_ai_engine_v5 = self.data, self.engine
        return self

    def __exit__(self, *a):
        B._smart_data, B.mosh_ai_engine_v5 = self.saved


# ─── الانقسام ──────────────────────────────────────────────────────────────────
def test_split_buy_and_sell():
    assert L.split_far_target(100, 99, 101, 106, True) == (102.5, 106)
    assert L.split_far_target(100, 101, 99, 94, False) == (97.5, 94)


def test_split_leaves_near_far_target_alone():
    assert L.split_far_target(100, 99, 101, 102.5, True) is None          # بالضبط 2.5R: هدفان كما هو
    assert L.split_far_target(100, 99, 101, 102, True) is None
    assert L.split_far_target(100, 100, 101, 106, True) is None           # وقف = دخول
    assert L.split_far_target(100, 99, 103, 101, True) is None            # هدف أول أبعد من 2.5R


def test_kill_switch():
    old = os.environ.get("TP_LADDER_ENABLED")
    try:
        os.environ.pop("TP_LADDER_ENABLED", None)
        assert L.ladder_enabled() is False                                # معطّل افتراضياً: النشر لا يغيّر شيئاً
        for v in ("0", "", "false", "off"):
            os.environ["TP_LADDER_ENABLED"] = v
            assert L.ladder_enabled() is False
        for v in ("1", "true", "ON"):
            os.environ["TP_LADDER_ENABLED"] = v
            assert L.ladder_enabled() is True
    finally:
        os.environ.pop("TP_LADDER_ENABLED", None)
        if old is not None:
            os.environ["TP_LADDER_ENABLED"] = old


def _analysis(tp1=101.0, tp2=106.0, rec="BUY"):
    return {"recommendation": rec, "levels": {"entry": 100.0, "stop_loss": 99.0 if rec == "BUY" else 101.0, "tp1": tp1, "tp2": tp2,
                                              "risk_reward": 6.0}, "take_profit_zones": [tp1, tp2]}


def test_legacy_engine_tp3_is_never_taken_as_ladder_target():
    """حادثة نشر 30/10: المحرك ينتج levels["tp3"] قديماً، فحُفظ هدف ثالث والسلّم معطّل."""
    def legacy(tp2):
        a = _analysis(tp2=tp2)
        a["levels"]["tp3"] = 120.0
        return a
    os.environ["TP_LADDER_ENABLED"] = "0"
    try:
        a = ENGINE._apply_tp_ladder(legacy(106.0), "BTCUSD", "1h")
        assert "ladder_tp3" not in a["levels"] and a["levels"]["tp2"] == 106.0
    finally:
        os.environ["TP_LADDER_ENABLED"] = "1"
    a = ENGINE._apply_tp_ladder(legacy(102.0), "BTCUSD", "1h")           # هدف قريب: هدفان، والقديم لا يُعرض
    assert "ladder_tp3" not in a["levels"] and "tp3" not in a["levels"]
    a = ENGINE._apply_tp_ladder(legacy(106.0), "BTCUSD", "1h")           # الثالث هو البعيد لا القديم
    assert a["levels"]["ladder_tp3"] == 106.0 and a["levels"]["tp3"] == 106.0


def test_writers_read_ladder_key_only():
    for f in ("app/api/bot.py", "app/api/signals.py", "../telegram-bot/bot.py"):
        if not (ROOT / f).exists():
            continue
        src = (ROOT / f).read_text(encoding="utf-8")
        assert 'levels.get("tp3")' not in src and 'lvls.get("tp3")' not in src and 'levels["tp3"]' not in src, f


def test_engine_splits_and_keeps_everything_else():
    a = ENGINE._apply_tp_ladder(_analysis(), "BTCUSD", "1h")
    lv = a["levels"]
    assert (lv["entry"], lv["stop_loss"], lv["tp1"], lv["tp2"], lv["tp3"]) == (100.0, 99.0, 101.0, 102.5, 106.0)
    assert lv["risk_reward"] == 6.0 and a["take_profit_zones"][:3] == [101.0, 102.5, 106.0]


def test_engine_after_cap_tp1():
    a = _analysis(tp1=104.0, tp2=106.0)
    a = ENGINE._apply_tp_ladder(ENGINE._cap_tp1(a, "BTCUSD", "1h"), "BTCUSD", "1h")
    assert (a["levels"]["tp1"], a["levels"]["tp2"], a["levels"]["tp3"]) == (101.0, 102.5, 106.0)


def test_engine_near_target_and_switch_off():
    a = ENGINE._apply_tp_ladder(_analysis(tp2=102.0), "BTCUSD", "1h")
    assert "tp3" not in a["levels"] and a["levels"]["tp2"] == 102.0
    os.environ["TP_LADDER_ENABLED"] = "0"
    try:
        a = ENGINE._apply_tp_ladder(_analysis(), "BTCUSD", "1h")
        assert "tp3" not in a["levels"] and a["levels"]["tp2"] == 106.0
    finally:
        os.environ["TP_LADDER_ENABLED"] = "1"


# ─── حلقة الرصد ───────────────────────────────────────────────────────────────
def _outs(res):
    return [t["status"] for t in res["triggered"]]


def test_full_climb_tp1_tp2_tp3():
    db = _db()
    with _Env() as e:
        s = _sig(db)
        assert _outs(_cycle(db, e.data, [(100.2, 99.9), (101.1, 100.3)])) == ["TP1_HIT"]
        db.refresh(s)
        assert s.status == SignalStatus.TP1_HIT and s.entry_executed is not None
        assert _outs(_cycle(db, e.data, [(100.2, 99.9), (101.1, 100.3), (102.6, 101.0)])) == ["TP2_HIT"]
        db.refresh(s)
        assert s.status == SignalStatus.TP2_HIT and s.tp3_hit_at is None and s.final_tp == TP2
        pts2 = s.points_earned
        res = _cycle(db, e.data, [(100.2, 99.9), (101.1, 100.3), (102.6, 101.0), (106.1, 102.4)])
        assert _outs(res) == ["TP3_HIT"] and res["triggered"][0]["tp3"] == TP3
        db.refresh(s)
        assert s.status == SignalStatus.TP2_HIT and s.tp3_hit_at is not None and s.final_tp == TP3
        assert s.points_earned > pts2
        assert _r_multiple(s.entry_price, s.stop_loss, s.take_profit_1, s.final_tp, "TP2_HIT") == 6.0
        assert _outs(_cycle(db, e.data, [(106.1, 102.4)])) == []         # انتهى الرصد
        assert e.engine.calls == ["WIN"]                                  # قرار واحد، لا ثلاثة


def test_stop_after_tp2_keeps_tp2():
    db = _db()
    with _Env() as e:
        s = _sig(db, status=SignalStatus.TP2_HIT, entered=True)
        res = _cycle(db, e.data, [(102.0, 98.9)])
        assert _outs(res) == []
        db.refresh(s)
        assert s.status == SignalStatus.TP2_HIT and s.tp3_hit_at is None and s.final_tp == TP2
        exp = s.expires_at if s.expires_at.tzinfo else s.expires_at.replace(tzinfo=timezone.utc)
        assert exp <= datetime.now(timezone.utc)
        assert _outs(_cycle(db, e.data, [(106.5, 102.0)])) == []         # خرج من الرصد: لا هدف ثالث بعد الوقف


def test_stop_wins_same_candle_as_tp3():
    db = _db()
    with _Env() as e:
        s = _sig(db, status=SignalStatus.TP2_HIT, entered=True)
        assert _outs(_cycle(db, e.data, [(106.5, 98.5)])) == []
        db.refresh(s)
        assert s.tp3_hit_at is None and s.status == SignalStatus.TP2_HIT


def test_single_candle_through_tp2_and_tp3():
    db = _db()
    with _Env() as e:
        s = _sig(db)
        path = [(106.5, 99.9)]
        assert _outs(_cycle(db, e.data, path)) == ["TP2_HIT"]
        db.refresh(s)
        assert s.status == SignalStatus.TP2_HIT and s.tp3_hit_at is None
        assert _outs(_cycle(db, e.data, path)) == ["TP3_HIT"]
        db.refresh(s)
        assert s.final_tp == TP3


def test_entry_must_be_touched_exactly():
    db = _db()
    with _Env() as e:
        s = _sig(db)
        # كل الأهداف "ضُربت" لكن أدنى سعر 100.01 — لم يُلمس الدخول 100.0
        assert _outs(_cycle(db, e.data, [(106.5, 100.01)])) == []
        db.refresh(s)
        assert s.status == SignalStatus.ACTIVE and s.entry_executed is None
        assert _outs(_cycle(db, e.data, [(106.5, 100.01), (100.5, 100.0)])) == []   # لُمس بالضبط، ولا هدف بعدها
        db.refresh(s)
        assert s.entry_executed is not None and s.status == SignalStatus.ACTIVE


def test_two_target_trade_unchanged():
    db = _db()
    with _Env() as e:
        s = _sig(db, tp3=None, tp2=103.0)
        assert _outs(_cycle(db, e.data, [(103.1, 99.9)])) == ["TP2_HIT"]
        db.refresh(s)
        assert s.status == SignalStatus.TP2_HIT and s.final_tp == 103.0
        assert _outs(_cycle(db, e.data, [(103.1, 99.9), (110.0, 98.0)])) == []  # نهائية كما كانت
        db.refresh(s)
        assert s.status == SignalStatus.TP2_HIT and e.engine.calls == ["WIN"]


def test_sl_before_any_target_still_loss():
    db = _db()
    with _Env() as e:
        s = _sig(db)
        assert _outs(_cycle(db, e.data, [(100.2, 98.9)])) == ["SL_HIT"]
        db.refresh(s)
        assert s.status == SignalStatus.SL_HIT and e.engine.calls == ["LOSS"]


def test_tp1_then_stop_keeps_tp1():
    db = _db()
    with _Env() as e:
        s = _sig(db, status=SignalStatus.TP1_HIT, entered=True)
        assert _outs(_cycle(db, e.data, [(100.5, 98.9)])) == []
        db.refresh(s)
        assert s.status == SignalStatus.TP1_HIT and s.final_tp == TP2


def test_sell_side_tp3():
    db = _db()
    with _Env() as e:
        s = _sig(db, status=SignalStatus.TP2_HIT, entered=True, side=SignalType.SELL, sl=101.0, tp1=99.0, tp2=97.5, tp3=94.0)
        assert _outs(_cycle(db, e.data, [(97.0, 93.9)])) == ["TP3_HIT"]
        db.refresh(s)
        assert s.final_tp == 94.0
        assert _r_multiple(s.entry_price, s.stop_loss, s.take_profit_1, s.final_tp, "TP2_HIT") == 6.0


def test_expired_while_waiting_tp3_stays_tp2():
    db = _db()
    with _Env() as e:
        s = _sig(db, status=SignalStatus.TP2_HIT, entered=True, expires_h=-1)
        assert _outs(_cycle(db, e.data, [(106.5, 102.0)])) == []
        db.refresh(s)
        assert s.status == SignalStatus.TP2_HIT and s.tp3_hit_at is None


def test_spot_instant_check_never_turns_locked_tp2_into_loss():
    """الفحص اللحظي للذهب والفضة: بعد الهدف الثاني لا يصير SL_HIT أبداً (خطر حقيقي لو فات شرط القفل)."""
    from app.services import tv_price_feed as TV
    saved = TV.tv_feed.get_price_sync
    db = _db()
    with _Env() as e:
        s = _sig(db, status=SignalStatus.TP2_HIT, entered=True, market="XAUUSD")
        TV.tv_feed.get_price_sync = lambda m: 98.0
        try:
            assert _outs(_cycle(db, e.data, [], range_check=False)) == []
            db.refresh(s)
            assert s.status == SignalStatus.TP2_HIT and s.tp3_hit_at is None
        finally:
            TV.tv_feed.get_price_sync = saved


def test_spot_instant_check_never_downgrades_locked_tp2():
    """سعر بين الهدفين الأول والثاني بعد القفل: لا ينزل إلى TP1. (عطّل شرط _tp2_locked بالفحص اللحظي ولم يلتقطه اختبار الوقف.)"""
    from app.services import tv_price_feed as TV
    saved = TV.tv_feed.get_price_sync
    db = _db()
    with _Env() as e:
        s = _sig(db, status=SignalStatus.TP2_HIT, entered=True, market="XAUUSD")
        TV.tv_feed.get_price_sync = lambda m: 101.5
        try:
            assert _outs(_cycle(db, e.data, [], range_check=False)) == []
            db.refresh(s)
            assert s.status == SignalStatus.TP2_HIT and s.tp3_hit_at is None
        finally:
            TV.tv_feed.get_price_sync = saved


def test_spot_instant_check_reaches_tp3():
    from app.services import tv_price_feed as TV
    saved = TV.tv_feed.get_price_sync
    db = _db()
    with _Env() as e:
        s = _sig(db, status=SignalStatus.TP2_HIT, entered=True, market="XAUUSD")
        TV.tv_feed.get_price_sync = lambda m: 106.5
        try:
            assert _outs(_cycle(db, e.data, [], range_check=False)) == ["TP3_HIT"]
            db.refresh(s)
            assert s.final_tp == TP3
        finally:
            TV.tv_feed.get_price_sync = saved


def test_waiting_tp3_counts_as_open_trade():
    db = _db()
    with _Env():
        s = _sig(db, status=SignalStatus.TP2_HIT, entered=True)
        assert B._open_equivalent_rows(db, s.market, s.signal_type, s.entry_price)
        s.tp3_hit_at = datetime.now(timezone.utc)
        db.commit()
        assert not B._open_equivalent_rows(db, s.market, s.signal_type, s.entry_price)


class _Skip(Exception):
    pass


# ─── الرسائل ──────────────────────────────────────────────────────────────────
def _msgs():
    if not (ROOT.parent / "telegram-bot").exists():      # صورة الخادم بلا مجلد البوت
        raise _Skip()
    sys.path.insert(0, str(ROOT.parent / "telegram-bot"))
    import messages as M
    import messages_en as ME
    return M, ME


FULL = {"market": "BTCUSD", "signal_type": "BUY", "entry_price": 100.0, "stop_loss": 99.0, "take_profit_1": 101.0,
        "take_profit_2": 102.5, "take_profit_3": 106.0}
OUT = {"market": "BTCUSD", "signal_type": "BUY", "entry": 100.0, "sl": 99.0, "tp1": 101.0, "tp2": 102.5, "tp3": 106.0,
       "pnl_pct": 6.0, "current_price": 106.4}


def test_signal_message_shows_three_targets():
    M, ME = _msgs()
    ar, en = M.signal_full(FULL, "بيتكوين", "ساعة", 70), ME.signal_full(FULL, "Bitcoin", "1h", 70)
    assert "الهدف 3" in ar and "106" in ar and "+6" in ar and "+2.5" in ar
    assert "TP3" in en and "106" in en


def test_two_target_message_unchanged():
    M, ME = _msgs()
    two = {k: v for k, v in FULL.items() if k != "take_profit_3"}
    two["take_profit_2"] = 102.0
    ar, en = M.signal_full(two, "بيتكوين", "ساعة", 70), ME.signal_full(two, "Bitcoin", "1h", 70)
    assert "الهدف 3" not in ar and "TP3" not in en and "🏁 الهدف 2" in ar and "🏁 TP2" in en


def test_outcome_tp3_uses_tp3_price_not_live_price():
    M, ME = _msgs()
    o = dict(OUT, status="TP3_HIT")
    assert M.outcome_result_r(o) == 6.0
    ar, en = M.outcome_subscriber(o, "بيتكوين"), ME.outcome_subscriber(o, "Bitcoin")
    assert "الهدف 3 تحقق" in ar and "106" in ar and "الهدف الكامل" in ar
    assert "TP3 hit" in en and "Full target" in en
    assert "الهدف الثالث" in M.outcome_expired(o, "بيتكوين") and "TP3" in ME.outcome_expired(o, "Bitcoin")


def test_tp2_message_points_to_tp3_only_when_it_exists():
    M, ME = _msgs()
    o = dict(OUT, status="TP2_HIT")
    assert M.outcome_result_r(o) == 2.5
    assert "الهدف 3" in M.outcome_subscriber(o, "بيتكوين") and "TP3" in ME.outcome_subscriber(o, "Bitcoin")
    two = dict(o, tp3=None)
    assert "الهدف الكامل" in M.outcome_subscriber(two, "بيتكوين") and "Full target" in ME.outcome_subscriber(two, "Bitcoin")


# ─── الإحصاء والعرض ───────────────────────────────────────────────────────────
def test_closed_decisions_uses_tp3_r_and_keeps_far_for_reviews():
    from app.models.market_config import MarketConfig
    from app.services.weekly_markets import closed_decisions
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng, tables=[Signal.__table__, User.__table__, MarketConfig.__table__])
    db = sessionmaker(bind=eng)()
    db.add(User(id=9, email="a@b.c", telegram_id="77", is_active=True, language="ar"))
    db.commit()
    a = _sig(db, i=1, status=SignalStatus.TP2_HIT, entered=True)
    a.tp3_hit_at = datetime.now(timezone.utc)
    b = _sig(db, i=2, status=SignalStatus.TP2_HIT, entered=True, entry=200.0, sl=199.0, tp1=201.0, tp2=202.5, tp3=206.0)
    c = _sig(db, i=3, status=SignalStatus.TP2_HIT, entered=True, tp3=None, tp2=103.0, entry=300.0, sl=299.0)
    c.take_profit_1, c.take_profit_2 = 301.0, 303.0
    for x in (a, b, c):
        x.current_price = 1.0                                             # مسجّلة من الرصد التلقائي
    db.commit()
    decs = {round(d["entry"]): d for d in closed_decisions(db, NOW - timedelta(days=1))}
    assert decs[100]["r"] == 6.0 and decs[100]["tp3_hit"] is True and decs[100]["far"] == 106.0
    assert decs[200]["r"] == 2.5 and decs[200]["tp3_hit"] is False and decs[200]["far"] == 206.0
    assert decs[300]["r"] == 3.0 and decs[300]["far"] == 303.0


def test_tp2r_review_rule_still_sees_far_target():
    """قاعدة المراقبة (6) TP2 ≥ 8R: بعد السلّم tp2 = 2.5R دائماً، فلا بد أن تقرأ البعيد."""
    d = {"entry": 100.0, "stop_loss": 99.0, "tp2": 102.5, "far": 110.0}
    tp2r = lambda d: abs((d.get("far") or d["tp2"] or d["entry"]) - d["entry"]) / max(1e-12, abs(d["entry"] - d["stop_loss"]))
    assert tp2r(d) == 10.0
    assert 'd.get("far")' in (ROOT / "diag_watch.py").read_text(encoding="utf-8")
    assert 'd.get("far")' in (ROOT / "diag_review.py").read_text(encoding="utf-8")


if __name__ == "__main__":
    tests =[(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for n, f in tests:
        try:
            f()
            print(f"✅ {n}")
        except _Skip:
            print(f"⏭ {n}")
        except Exception as e:
            failed += 1
            import traceback
            print(f"❌ {n}: {type(e).__name__}: {e}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} نجح")
    sys.exit(1 if failed else 0)
