"""
اختبارات إصلاح مستويات صفقات الظل — المرحلة 1 (2026-10-18).

التشغيل (بلا pytest، بلا قاعدة بيانات حقيقية — SQLite بالذاكرة وشموع مُصطنعة):
  cd backend && python tests/test_shadow_levels.py
ويعمل أيضاً مع pytest إن كان مثبتاً.

يغطي:
  1) normalize_rejected_levels: شراء/بيع، صالحة/معكوسة، السماحية، تبديل TP1/TP2، النواقص.
  2) تطابق قاعدة التحقق مع فحص الجهة الحي (_institutional_gate Rule 6) — حارس: يفشل إن تغيّرت القاعدة الحية.
  3) record_shadow: يحفظ الصالحة بـlevels_version=1 ويرفض المعكوسة (لا صف) — لكل المسارات.
  4) التقييم بعد الإصلاح: TP1 وTP2 وSL للشراء والبيع بشموع 5m مُصطنعة عبر _verify_signal_outcome_core نفسها،
     ومثال المستويات المعكوسة القديم (خسارة فورية) لإثبات ما كان يحدث.
  5) المسار الحي لا يتغيّر: ملفات/دوال الإرسال لا تستورد shadow_levels، وفحص الجهة الحي بنصّه الأصلي.
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

from app.services.shadow_levels import normalize_rejected_levels, final_levels_valid, LEVELS_VERSION  # noqa: E402


def L(entry, sl, tp1, tp2=None):
    return {"entry": entry, "stop_loss": sl, "tp1": tp1, "tp2": tp2}


# ─── 1) normalize_rejected_levels ───────────────────────────────────────────────
def test_buy_valid_passes_unchanged():
    lv, bad = normalize_rejected_levels("BUY", L(100, 99, 101, 103))
    assert bad is None and lv["stop_loss"] == 99 and lv["tp1"] == 101 and lv["tp2"] == 103


def test_sell_valid_passes_unchanged():
    lv, bad = normalize_rejected_levels("SELL", L(100, 101, 99, 97))
    assert bad is None and lv["tp1"] == 99 and lv["tp2"] == 97


def test_buy_inverted_sl_rejected():
    assert normalize_rejected_levels("BUY", L(100, 101, 99, 97)) == (None, "BUY_SL_ABOVE_ENTRY")


def test_sell_inverted_sl_rejected():
    # الحالة الشائعة بالتدقيق: رفض "بيع" بمستويات بُنيت للشراء
    assert normalize_rejected_levels("SELL", L(100, 99, 101, 103)) == (None, "SELL_SL_BELOW_ENTRY")


def test_buy_tp1_wrong_side_rejected():
    assert normalize_rejected_levels("BUY", L(100, 99, 99.5, 103))[1] == "BUY_TP1_BELOW_ENTRY"


def test_sell_tp1_wrong_side_rejected():
    assert normalize_rejected_levels("SELL", L(100, 101, 100.5, 97))[1] == "SELL_TP1_ABOVE_ENTRY"


def test_buy_tp2_before_tp1_swapped_like_live():
    lv, bad = normalize_rejected_levels("BUY", L(100, 99, 103, 101))
    assert bad is None and lv["tp1"] == 101 and lv["tp2"] == 103


def test_sell_tp2_before_tp1_swapped_like_live():
    lv, bad = normalize_rejected_levels("SELL", L(100, 101, 97, 99))
    assert bad is None and lv["tp1"] == 99 and lv["tp2"] == 97


def test_swap_into_wrong_side_rejected():
    # الحي لا يعيد الفحص بعد التبديل؛ الظل أشد: هدف بالجهة الخطأ بعد التبديل يُرفض
    assert normalize_rejected_levels("BUY", L(100, 99, 102, 98))[1] == "BUY_TP1_BELOW_ENTRY_AFTER_SWAP"
    assert normalize_rejected_levels("SELL", L(100, 101, 98, 102))[1] == "SELL_TP1_ABOVE_ENTRY_AFTER_SWAP"


def test_tolerance_matches_live_epsilon():
    # وقف شراء أدنى من الدخول بأقل من 0.01% ← الحي يرفضه (sl >= entry*0.9999)
    assert normalize_rejected_levels("BUY", L(100, 99.995, 101))[1] == "BUY_SL_ABOVE_ENTRY"
    assert normalize_rejected_levels("BUY", L(100, 99.98, 101))[1] is None
    assert normalize_rejected_levels("SELL", L(100, 100.005, 99))[1] == "SELL_SL_BELOW_ENTRY"


def test_missing_levels_rejected():
    assert normalize_rejected_levels("BUY", L(0, 99, 101))[1] == "MISSING_ENTRY_PRICE"
    assert normalize_rejected_levels("BUY", L(100, None, 101))[1] == "MISSING_SL_OR_TP1"
    assert normalize_rejected_levels("SELL", L(100, 101, None))[1] == "MISSING_SL_OR_TP1"
    assert normalize_rejected_levels("WAIT", L(100, 99, 101))[1] == "INVALID_SIDE"


def test_input_not_mutated():
    raw = L(100, 99, 103, 101)
    normalize_rejected_levels("BUY", raw)
    assert raw == L(100, 99, 103, 101)


def test_final_levels_valid():
    assert final_levels_valid("BUY", 100, 99, 101, None) is None
    assert final_levels_valid("BUY", 100, 99, 101, 100.5) is None      # TP2 قبل TP1 مقبول = لا هدف ثانٍ
    assert final_levels_valid("SELL", 100, 99, 101) == "SELL_SL_BELOW_ENTRY"
    assert final_levels_valid("BUY", 100, 101, 102) == "BUY_SL_ABOVE_ENTRY"


# ─── 2) تطابق مع فحص الجهة الحي ─────────────────────────────────────────────────
def test_live_gate_rule6_text_unchanged():
    src = (ROOT / "app/services/ai_engine_v5.py").read_text(encoding="utf-8")
    for needle in ('if sl > 0 and sl >= entry * 0.9999:', 'return self._hard_reject(analysis, "BUY_SL_ABOVE_ENTRY")',
                   'if tp1 > 0 and tp1 <= entry * 1.0001:', 'return self._hard_reject(analysis, "BUY_TP1_BELOW_ENTRY")',
                   'if sl > 0 and sl <= entry * 1.0001:', 'return self._hard_reject(analysis, "SELL_SL_BELOW_ENTRY")',
                   'if tp1 > 0 and tp1 >= entry * 0.9999:', 'return self._hard_reject(analysis, "SELL_TP1_ABOVE_ENTRY")',
                   'if tp2 and tp1 and tp1 > tp2:', 'if tp2 and tp1 and tp1 < tp2:'):
        assert needle in src, f"فحص الجهة الحي تغيّر — حدّث shadow_levels.py ليطابقه: {needle}"


def test_parity_with_live_rule_on_grid():
    """تنفيذ مستقل لقاعدة Rule 6 الحية حرفياً (للحالات التي فيها كل المستويات > 0) ← نفس قرار الظل."""
    def live(side, e, sl, t1, t2):
        if side == "BUY":
            if sl >= e * 0.9999: return "BUY_SL_ABOVE_ENTRY"
            if t1 <= e * 1.0001: return "BUY_TP1_BELOW_ENTRY"
        else:
            if sl <= e * 1.0001: return "SELL_SL_BELOW_ENTRY"
            if t1 >= e * 0.9999: return "SELL_TP1_ABOVE_ENTRY"
        return None
    vals = [98.0, 99.0, 99.995, 100.0, 100.005, 101.0, 102.0]
    n = 0
    for side in ("BUY", "SELL"):
        for sl in vals:
            for t1 in vals:
                lv, bad = normalize_rejected_levels(side, L(100.0, sl, t1))
                exp = live(side, 100.0, sl, t1, None)
                assert bad == exp, (side, sl, t1, bad, exp)
                n += 1
    assert n == 98


# ─── 3) record_shadow ──────────────────────────────────────────────────────────
def _db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.database import Base
    from app.models.user import User
    from app.models.shadow_signal import ShadowSignal
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng, tables=[User.__table__, ShadowSignal.__table__])
    return sessionmaker(bind=eng)()


def test_record_shadow_saves_valid_with_version_and_refuses_inverted():
    from app.models.shadow_signal import ShadowSignal
    from app.services.weekend_policy import record_shadow
    db = _db()
    exp = datetime.now(timezone.utc) + timedelta(hours=3)
    ok = record_shadow(db, source="rejected", reason="ZONE_CONFLICT_SELL_IN_DISCOUNT", symbol="XAUUSD", timeframe="15m",
                       signal_type="SELL", entry=4160, sl=4166, tp1=4154, tp2=4142, expires_at=exp)
    bad = record_shadow(db, source="rejected", reason="HTF_CONFLICT_REJECTED", symbol="XAUUSD", timeframe="15m",
                        signal_type="SELL", entry=4160, sl=4154, tp1=4166, tp2=4178, expires_at=exp)
    wk = record_shadow(db, source="scanner", symbol="BTCUSD", timeframe="1h", signal_type="BUY",
                       entry=80000, sl=79000, tp1=81000, tp2=83000, expires_at=exp)        # مسار العطلة
    rows = db.query(ShadowSignal).all()
    assert ok and wk and bad is None
    assert len(rows) == 2 and all(r.levels_version == LEVELS_VERSION for r in rows)


# ─── 4) التقييم بعد الإصلاح: TP1 / TP2 / SL ──────────────────────────────────────
def _run_eval(side, entry, sl, tp1, tp2, path):
    """path = [(high, low, close), ...] شموع 5m بعد الإنشاء. يعيد detected و r_multiple من الأداة الحقيقية."""
    import pandas as pd
    import app.api.admin as A
    t0 = datetime(2026, 10, 14, 10, 0, tzinfo=timezone.utc)
    bars = [(t0 - timedelta(minutes=5), entry, entry, entry)] + \
           [(t0 + timedelta(minutes=5 * (i + 1)), h, l, c) for i, (h, l, c) in enumerate(path)]
    df = pd.DataFrame([(b[0], b[1], b[2], b[3]) for b in bars], columns=["datetime", "high", "low", "close"])

    async def fake(*a, **k):
        return df
    orig = A._smart_data.get_ohlcv
    A._smart_data.get_ohlcv = fake
    try:
        sig = SimpleNamespace(created_at=t0 + timedelta(minutes=1), expires_at=t0 + timedelta(hours=3),
                              entry_price=entry, stop_loss=sl, take_profit_1=tp1, take_profit_2=tp2,
                              signal_type=side, status="SHADOW", market="EURUSD")
        return asyncio.run(A._verify_signal_outcome_core(sig))
    finally:
        A._smart_data.get_ohlcv = orig


def test_eval_buy_tp1_then_sl_counts_tp1():
    r = _run_eval("BUY", 1.1000, 1.0990, 1.1010, 1.1030,
                  [(1.1002, 1.0998, 1.1000), (1.1011, 1.1001, 1.1009), (1.1005, 1.0989, 1.0990)])
    assert r["detected"] == "TP1_HIT" and r["r_multiple"] == 1.0


def test_eval_buy_tp2():
    r = _run_eval("BUY", 1.1000, 1.0990, 1.1010, 1.1030,
                  [(1.1002, 1.0998, 1.1000), (1.1015, 1.1001, 1.1012), (1.1031, 1.1010, 1.1029)])
    assert r["detected"] == "TP2_HIT" and r["r_multiple"] == 3.0


def test_eval_buy_sl():
    r = _run_eval("BUY", 1.1000, 1.0990, 1.1010, 1.1030,
                  [(1.1002, 1.0998, 1.1000), (1.1001, 1.0989, 1.0991)])
    assert r["detected"] == "SL_HIT" and r["r_multiple"] == -1.0


def test_eval_sell_tp1_tp2_sl():
    path_tp1 = [(1.1002, 1.0998, 1.1000), (1.0999, 1.0989, 1.0991), (1.1011, 1.0995, 1.1010)]
    path_tp2 = [(1.1002, 1.0998, 1.1000), (1.0999, 1.0985, 1.0987), (1.0990, 1.0969, 1.0971)]
    path_sl = [(1.1002, 1.0998, 1.1000), (1.1011, 1.0999, 1.1009)]
    for path, det, r in ((path_tp1, "TP1_HIT", 1.0), (path_tp2, "TP2_HIT", 3.0), (path_sl, "SL_HIT", -1.0)):
        res = _run_eval("SELL", 1.1000, 1.1010, 1.0990, 1.0970, path)
        assert res["detected"] == det and res["r_multiple"] == r, (det, res)


def test_old_inverted_levels_were_instant_loss_and_are_now_refused():
    """ما كان يحدث قبل الإصلاح: بيع بمستويات شراء ← SL على شمعة الدخول نفسها رغم أن السعر لم يتحرك."""
    flat = [(1.1002, 1.0998, 1.1000), (1.1003, 1.0997, 1.1001)]
    old = _run_eval("SELL", 1.1000, 1.0990, 1.1010, 1.1030, flat)
    assert old["detected"] == "SL_HIT" and old["r_multiple"] == -1.0
    assert normalize_rejected_levels("SELL", L(1.1000, 1.0990, 1.1010, 1.1030))[0] is None


# ─── 5) المسار الحي لا يتغيّر ────────────────────────────────────────────────────
def test_live_paths_do_not_use_shadow_levels():
    """shadow_levels يُستورد فقط من مسار تسجيل الظل (record_shadow وكتلة الرفض بـbot_analyze) — لا من المحرك ولا الإرسال."""
    users = []
    for p in (ROOT / "app").rglob("*.py"):
        if "from app.services.shadow_levels import" in p.read_text(encoding="utf-8"):
            users.append(p.relative_to(ROOT).as_posix())
    assert sorted(users) == ["app/api/bot.py", "app/services/weekend_policy.py"], users
    bot = (ROOT / "app/api/bot.py").read_text(encoding="utf-8")
    i = bot.index("from app.services.shadow_levels import normalize_rejected_levels")
    block_start = bot.rindex("_LEARN_REJECTIONS", 0, i)
    assert i - block_start < 600, "الاستيراد يجب أن يكون داخل كتلة تسجيل الظل للصفقات المرفوضة فقط"


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for n, f in tests:
        try:
            f()
            print(f"✅ {n}")
        except Exception as e:
            failed += 1
            print(f"❌ {n}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} نجح")
    sys.exit(1 if failed else 0)
