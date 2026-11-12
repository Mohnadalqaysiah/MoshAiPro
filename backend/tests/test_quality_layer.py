"""
طبقة الجودة — المرحلة 1 (2026-11-12): منطق diag_quality_layer على بيانات مصطنعة نعرف جوابها، ومحمّل قاعدة البيانات.

  cd backend && python tests/test_quality_layer.py      (أو pytest)
"""
import os
import random
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

import diag_quality_layer as Q  # noqa: E402

UTC = timezone.utc


def test_flatten_alignment_signs_and_sessions():
    f = {"htf_trend": "BULLISH", "ltf_trend": "BEARISH", "momentum_dir": "UP", "market_state": "RANGING",
         "hour_utc": 13, "weekday": 0, "with_h4_trend": True, "is_crypto": True,
         "h4": {"trend": "UP", "dist_ema_pct": 2.0, "ema_slope_pct": 0.5, "ret_24h_pct": -1.0},
         "btc_h4": {"trend": "DOWN"}, "confidence": 70}
    cat, num = Q.flatten(f, "BUY", "1h", "crypto")
    assert (cat["htf_with"], cat["ltf_with"], cat["mom_with"], cat["btc_with"]) == ("مع الصفقة", "ضد الصفقة", "مع الصفقة", "ضد الصفقة")
    assert cat["session"] == "نيويورك 12-17" and cat["weekday"] == "الإثنين" and cat["with_h4_trend"] == "نعم"
    assert (num["stretch"], num["slope_with"], num["ret24_with"]) == (2.0, 0.5, -1.0)
    cat, num = Q.flatten(f, "SELL", "1h", "forex")
    assert cat["htf_with"] == "ضد الصفقة" and num["stretch"] == -2.0 and num["ret24_with"] == 1.0
    assert Q.flatten({"is_crypto": False, "htf_trend": "RANGING"}, "BUY", "4h", "forex")[0]["htf_with"] == "—"
    assert [Q._session(h) for h in (3, 8, 18, 22, None)] == ["آسيا 00-07", "لندن 07-12", "بعد نيويورك 17-21",
                                                            "متأخرة 21-24", "—"]


def _synthetic(seed=7):
    """نمط مزروع: حالة السوق RANGING تربح 25% فقط في كل الأسواق والفترتين؛ الباقي 58%. التقلب ضجيج خالص."""
    rnd = random.Random(seed)
    recs = []
    t0 = datetime(2026, 10, 14, tzinfo=UTC)
    for i in range(900):
        t = t0 + timedelta(hours=i * 0.75)
        group = rnd.choice(["crypto", "forex", "gold"])
        ranging = rnd.random() < 0.22
        win = rnd.random() < (0.25 if ranging else 0.58)
        f = {"market_state": "RANGING" if ranging else "TRENDING", "volatility": rnd.choice(["LOW", "NORMAL", "HIGH"]),
             "confidence": rnd.uniform(40, 90), "hour_utc": rnd.randrange(24), "weekday": rnd.randrange(7),
             "atr_pct": rnd.uniform(0.1, 2.0) * (10 if group == "crypto" else 1)}
        recs.append(Q.record(t, group, 1.6 if win else -1.0, f, rnd.choice(["BUY", "SELL"]), rnd.choice(["1h", "4h"])))
    return recs


def test_planted_pattern_found_noise_rejected_and_grade_generalises():
    recs = _synthetic()
    train = [r for r in recs if r["t"] < Q.SPLIT]
    test = [r for r in recs if r["t"] >= Q.SPLIT]
    assert len(train) > 300 and len(test) > 100
    shadow = _synthetic(seed=99)
    res, lab, _ = Q.evaluate(train, test, shadow, Q.fit_cutoffs(train))
    hit = [c for c in res if c["feat"] == "market_state" and c["val"] == "RANGING"]
    assert hit and hit[0]["kind"] == "weak" and hit[0]["held"] and hit[0]["consistent"] and hit[0]["d_sh"] < 0
    noise_held = [c for c in res if c["feat"] == "volatility" and c["held"] and c["consistent"]]
    assert not noise_held, noise_held                                            # الضجيج لا يصمد
    weak = Q.grade_bins(res)
    assert ("market_state", "RANGING") in weak and hit[0]["shadow_ok"]
    assert all(c["consistent"] and c["shadow_tr_ok"] for c in res if (c["feat"], c["val"]) in weak)
    assert ("weekday", "الثلاثاء") not in weak                                  # يوم صدفة: الظل لا يؤكده فلا يدخل الدرجة
    fake = [c for c in res if c["feat"] == "weekday" and c["held"]]
    assert all(not c["shadow_ok"] for c in fake)                                # يوم صدفة صمد بالاختبار لا يأخذ ✅
    gt = Q.grade_table(test, lab, weak)
    assert gt["A"][0] > 30 and gt["A"][1] > gt["B+C"][1] + 15                    # الدرجة تفصل على ما لم تره


def test_group_relative_buckets_avoid_market_mix():
    recs = _synthetic()
    train = [r for r in recs if r["t"] < Q.SPLIT]
    cuts = Q.fit_cutoffs(train)
    c_lo, c_hi = cuts["group"]["atr_pct"]["crypto"]
    f_lo, f_hi = cuts["group"]["atr_pct"]["forex"]
    assert c_lo > f_hi                                       # الكريبتو بمقياس آخر: أثلاثه منفصلة عن الفوركس
    lab = Q.labels(Q.record(Q.SPLIT, "forex", 1, {"atr_pct": f_hi + 0.01}, "BUY", "1h"), cuts)
    assert lab["atr_pct"] == "مرتفع"                         # مرتفع نسبةً للفوركس وإن كان منخفضاً للكريبتو


# ─── المحمّل على قاعدة بيانات حقيقية مصغّرة ─────────────────────────────────
def test_loaders_link_fingerprints_to_decisions_and_shadow():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.database import Base
    from app.models.market_config import MarketConfig
    from app.models.shadow_signal import ShadowSignal
    from app.models.signal import Signal, SignalStatus, SignalType
    from app.models.signal_feature import SignalFeature
    from app.models.user import User

    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng, tables=[User.__table__, Signal.__table__, ShadowSignal.__table__,
                                          MarketConfig.__table__, SignalFeature.__table__])
    s = sessionmaker(bind=eng)()
    s.add(User(id=1, email="a@x.com", password_hash="x"))
    s.add(MarketConfig(symbol="BTCUSD", display_name="BTC", category="crypto"))
    t = datetime(2026, 10, 20, 10, 0, tzinfo=UTC)

    def sig(i, created, status, entry):
        # كل قرار بمستوياته (نفس المستويات وهي مفتوحة = نفس القرار المعاد إصداره، تدمجه المنصة عمداً)
        s.add(Signal(id=i, user_id=1, market="BTCUSD", timeframe="1h", signal_type=SignalType.BUY, status=status,
                     entry_price=entry, stop_loss=entry - 1, take_profit_1=entry + 1, take_profit_2=entry + 2.5,
                     current_price=entry, ai_confidence=70, broadcast_sent=True, created_at=created,
                     expires_at=created + timedelta(hours=24)))

    sig(1, t, SignalStatus.TP1_HIT, 100.0)                                # ممثّل القرار، بلا بصمة
    sig(2, t + timedelta(seconds=40), SignalStatus.TP1_HIT, 100.0)         # نفس القرار (ضمن دقيقتين) — البصمة هنا
    sig(3, t + timedelta(days=2), SignalStatus.SL_HIT, 110.0)              # قرار ثانٍ ببصمته
    sig(4, t + timedelta(days=4), SignalStatus.SL_HIT, 120.0)              # قرار ثالث بلا بصمة
    s.add(SignalFeature(signal_id=2, market="BTCUSD", timeframe="1h", features={"market_state": "TRENDING"}, created_at=t))
    s.add(SignalFeature(signal_id=3, market="BTCUSD", timeframe="1h", features={"market_state": "RANGING"}, created_at=t))
    s.add(ShadowSignal(id=10, source="scanner", reason="HTF_CONFLICT_REJECTED", market="BTCUSD", timeframe="1h",
                       signal_type="BUY", entry_price=100.0, stop_loss=99.0, take_profit_1=101.0, status="CLOSED",
                       outcome="SL_HIT", r_multiple=-1.0, levels_version=1, created_at=t))
    s.add(ShadowSignal(id=11, source="scanner", reason="tpl:sniper", market="BTCUSD", timeframe="1h",       # قالب: يُستثنى
                       signal_type="BUY", entry_price=100.0, stop_loss=99.0, take_profit_1=101.0, status="CLOSED",
                       outcome="TP1_HIT", r_multiple=1.0, created_at=t))
    s.add(SignalFeature(shadow_id=10, market="BTCUSD", timeframe="1h", features={"market_state": "RANGING"}, created_at=t))
    s.add(SignalFeature(shadow_id=11, market="BTCUSD", timeframe="1h", features={"market_state": "RANGING"}, created_at=t))
    s.commit()

    live, n_decs, missing = Q.load_live(s)
    assert (n_decs, len(live), missing) == (3, 2, 1)
    by_state = {r["cat"]["market_state"]: r for r in live}
    assert by_state["TRENDING"]["win"] and by_state["TRENDING"]["group"] == "crypto"
    assert not by_state["RANGING"]["win"] and by_state["RANGING"]["r"] == -1.0
    shadow, n_total = Q.load_shadow(s)
    assert (n_total, len(shadow)) == (1, 1) and shadow[0]["r"] == -1.0


def test_report_runs_end_to_end_on_synthetic():
    import contextlib
    import io
    recs = _synthetic()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        Q.report(recs, len(recs) + 5, 5, _synthetic(seed=3), 900, datetime(2026, 11, 12, tzinfo=UTC))
    out = buf.getvalue()
    assert "حالة السوق: RANGING" in out and "✅ صمد بالاختبار، ويتكرر بالأسواق، ويؤكده الظل" in out
    assert "B+C:" in out and "داخل كل سوق" in out and "الجمعة" not in out.split("الدرجة المقترحة")[0].split("✅")[0]


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
