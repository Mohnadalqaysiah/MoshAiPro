"""
اختبارات المرحلة 2 (2026-10-18) — قراءة صفقات الظل في التقارير (shadow_stats، تبويب الأدمن، diag_review).

  cd backend && python tests/test_shadow_stats.py      (أو pytest)

يغطي: النطاق (نظيف/قديم/الكل)، تجميع الفرص المستقلة وممثّلها، R بعد سبريد الجدول، عتبة الحكم (30 فرصة)،
نقطة الأدمن /shadow-signals، وأن diag_review يقرأ النظيف والفرص ويُبقي قواعده المسجّلة كما هي.
"""
import io
import os
import sys
import types
from contextlib import redirect_stdout
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

from app.services import shadow_stats as st  # noqa: E402

T0 = datetime(2026, 10, 19, 10, 0, tzinfo=timezone.utc)
_id = [0]


def row(reason="HTF_CONFLICT_REJECTED", market="XAUUSD", tf="15m", side="SELL", entry=4160.0, sl=4166.0, tp1=4154.0,
        tp2=4142.0, outcome="SL_HIT", r=-1.0, minutes=0, version=1, exp_h=3, exit_min=None):
    from app.models.shadow_signal import ShadowSignal
    _id[0] += 1
    c = T0 + timedelta(minutes=minutes)
    return ShadowSignal(id=_id[0], source="rejected", reason=reason, market=market, timeframe=tf, signal_type=side,
                        entry_price=entry, stop_loss=sl, take_profit_1=tp1, take_profit_2=tp2, outcome=outcome,
                        r_multiple=r, created_at=c, expires_at=c + timedelta(hours=exp_h),
                        exit_time=(c + timedelta(minutes=exit_min)) if exit_min is not None else None,
                        levels_version=version, signal_hash=f"h{_id[0]}")


# ─── النطاق ────────────────────────────────────────────────────────────────────
def test_scope_clean_legacy_all():
    clean, legacy = row(version=1), row(version=None)
    tpl = row(reason="tpl:gold_session_sell", version=None)          # القوالب لم تتأثر بالعطل
    rows = [clean, legacy, tpl]
    assert st.filter_scope(rows, "clean") == [clean, tpl]
    assert st.filter_scope(rows, "legacy") == [legacy]
    assert len(st.filter_scope(rows, "all")) == 3


# ─── الفرص المستقلة ─────────────────────────────────────────────────────────────
def test_same_idea_two_timeframes_is_one_opportunity_rep_is_earliest():
    a = row(tf="15m", outcome="SL_HIT", r=-1.0, minutes=0)
    b = row(tf="1h", entry=4161.0, outcome="TP2_HIT", r=3.0, minutes=30)
    opps = st.opportunities([b, a])
    assert len(opps) == 1 and opps[0][0] is a                     # الأقدم يمثّل — لا انتقاء بالنتيجة
    s = st.summarize([a, b])
    assert s["rows"] == 2 and s["opportunities"] == 1 and s["duplicates"] == 1
    assert s["decided"] == 1 and s["losses"] == 1 and s["r_gross"] == -1.0


def test_new_trade_after_first_closed_is_independent():
    a = row(minutes=0, exit_min=20)                                 # أُغلقت بعد 20 دقيقة
    b = row(minutes=40, entry=4160.5)                               # بعد إغلاقها = فكرة جديدة
    assert len(st.opportunities([a, b])) == 2


def test_distinct_side_price_or_time_are_independent():
    a = row(minutes=0)
    assert len(st.opportunities([a, row(side="BUY", sl=4154, tp1=4166, minutes=5)])) == 2
    assert len(st.opportunities([a, row(entry=4180.0, minutes=5)])) == 2          # > 0.3%
    assert len(st.opportunities([a, row(minutes=150, exp_h=24)])) == 2            # > ساعتين


def test_templates_never_clustered():
    a = row(reason="tpl:gold_session_sell", minutes=0)
    b = row(reason="tpl:gold_session_sell", minutes=10)
    assert len(st.opportunities([a, b])) == 2


# ─── السبريد ───────────────────────────────────────────────────────────────────
def test_net_r_uses_spread_table_and_templates_are_net_already():
    s = row(entry=4160, sl=4166, outcome="TP1_HIT", r=1.0)          # سبريد الذهب 0.30 ÷ وقف 6 = 0.05R
    assert abs(st.net_r(s) - 0.95) < 1e-9
    t = row(reason="tpl:gold_session_sell", r=1.4)
    assert st.net_r(t) == 1.4
    unknown = row(market="ZZZUSD", r=1.0)
    assert st.net_r(unknown) is None


def test_summary_gross_and_net():
    rows = [row(minutes=i * 200, outcome="TP1_HIT", r=1.0) for i in range(3)] + [row(minutes=900, r=-1.0)]
    s = st.summarize(rows)
    assert s["decided"] == 4 and s["wins"] == 3 and s["r_gross"] == 2.0
    assert abs(s["r_net"] - (2.0 - 4 * 0.05)) < 1e-6


# ─── عتبة الحكم ─────────────────────────────────────────────────────────────────
def test_verdict_needs_30_independent_and_uses_net():
    few = [row(minutes=i * 200, outcome="TP1_HIT", r=1.0) for i in range(29)]
    assert st.summarize(few)["verdict"] == "insufficient"
    # 30 فرصة: إجمالي موجب (+0.1R) لكن سالب بعد سبريد كبير ← الحكم على الصافي
    rows = [row(market="EURUSD", entry=1.1, sl=1.0998, tp1=1.1002, minutes=i * 200,
                outcome="TP1_HIT" if i % 2 else "SL_HIT", r=1.2 if i % 2 else -1.0) for i in range(30)]
    s = st.summarize(rows)
    assert s["decided"] == 30 and s["avg_gross"] > 0 and s["avg_net"] < 0
    assert s["verdict"] == "blocks_losers"
    win = [row(minutes=i * 200, outcome="TP1_HIT", r=1.0) for i in range(30)]
    assert st.summarize(win)["verdict"] == "blocks_winners"
    tpl = [row(reason="tpl:gold_session_sell", minutes=i * 200, outcome="TP2_HIT", r=1.5) for i in range(30)]
    assert st.summarize(tpl)["verdict"] == "positive"


# ─── نقطة الأدمن ────────────────────────────────────────────────────────────────
def _db(rows):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.database import Base
    from app.models.user import User
    from app.models.shadow_signal import ShadowSignal
    from app.models.signal import Signal
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng, tables=[User.__table__, ShadowSignal.__table__, Signal.__table__])
    db = sessionmaker(bind=eng)()
    db.add_all(rows)
    db.commit()
    return db


def test_admin_endpoint_defaults_to_clean_independent():
    import app.api.admin as A
    now = datetime.now(timezone.utc)
    rows = [row(minutes=0), row(tf="1h", entry=4161, minutes=20, outcome="TP2_HIT", r=3.0),   # فرصة واحدة نظيفة
            row(version=None, side="SELL", sl=4154, tp1=4166, minutes=60)]                    # قديمة معكوسة
    for r in rows:
        r.created_at = now - timedelta(hours=2) + (r.created_at - T0)
        r.expires_at = r.created_at + timedelta(hours=3)
    db = _db(rows)
    res = A.admin_shadow_signals(reason=None, days=30, page=1, page_size=50, scope="clean", admin=None, db=db)
    assert res["counts"] == {"clean": 2, "legacy": 1}
    b = res["summary"][0]
    assert b["rows"] == 2 and b["opportunities"] == 1 and b["decided"] == 1 and b["r_gross"] == -1.0
    assert b["verdict"] == "insufficient"
    assert {i["duplicate"] for i in res["items"]} == {True, False} and not any(i["legacy"] for i in res["items"])
    leg = A.admin_shadow_signals(reason=None, days=30, page=1, page_size=50, scope="legacy", admin=None, db=db)
    assert leg["total"] == 1 and leg["items"][0]["legacy"] is True


# ─── diag_review ───────────────────────────────────────────────────────────────
def test_diag_review_reads_clean_opportunities_rules_unchanged():
    import diag_review as R
    src = (ROOT / "diag_review.py").read_text(encoding="utf-8")
    for rule in ("n >= 30, avg > 0.3, h1 is not None and h1 > 0 and h2 > 0",
                 "n >= 30, avg < -0.3, h1 is not None and h1 < 0 and h2 < 0",
                 'len(cw) >= 30 and avg >= 0'):
        assert rule in src, f"قاعدة مسجّلة تغيّرت: {rule}"
    # 40 صفاً نظيفاً = 20 فرصة (كل فكرة على فريمين) + 30 قديمة يجب ألا تدخل
    now = datetime.now(timezone.utc)
    rows = []
    for i in range(20):
        a = row(minutes=i * 300, outcome="TP1_HIT", r=1.0)
        b = row(tf="1h", entry=4160.5, minutes=i * 300 + 10, outcome="TP1_HIT", r=1.0)
        rows += [a, b]
    rows += [row(version=None, minutes=7000 + i * 300, r=-1.0) for i in range(30)]
    for r in rows:
        r.created_at = now - timedelta(days=5) + (r.created_at - T0)
        r.expires_at = r.created_at + timedelta(hours=3)
    db = _db(rows)
    R.SessionLocal = lambda: db
    import app.services.weekly_markets as W
    W.closed_decisions = lambda db, since: []
    buf = io.StringIO()
    with redirect_stdout(buf):
        R.main()
    out = buf.getvalue()
    assert "مستبعد (قبل إصلاح المستويات): 30 صفاً" in out
    assert "(40 صفاً → 20 فرصة محسومة)" in out
    assert "ن=20" in out and "بعد سبريد الجدول" in out


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for n, f in tests:
        try:
            f()
            print(f"✅ {n}")
        except Exception as e:
            failed += 1
            import traceback
            print(f"❌ {n}: {type(e).__name__}: {e}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} نجح")
    sys.exit(1 if failed else 0)
