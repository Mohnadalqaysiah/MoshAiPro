"""
اختبارات مكتبة القوالب (2026-11-03) — الطلقة الفضية بنوافذها، وسلامة كل قالب، وشروط القبول.

  cd backend && python tests/test_templates.py      (أو pytest)
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@127.0.0.1:1/x")

import diag_template_backtest as D  # noqa: E402
from app.services import strategy_engine as E  # noqa: E402
from app.services import strategy_templates as T  # noqa: E402

UTC = timezone.utc
FRONT = (ROOT.parent / "frontend" / "src" / "pages" / "StrategyBuilder.jsx").read_text(encoding="utf-8")


def _in_window(t):
    return E.SUPPORTED_CONDITION_TYPES["silverbullet"]({"_eval_time_utc": t}, None)


def test_windows_in_winter_are_ny_minus_five():
    d = (2026, 12, 2)
    for h, m, want in [(7, 59, False), (8, 0, True), (8, 59, True), (9, 0, False),          # 03-04 نيويورك
                       (14, 59, False), (15, 0, True), (15, 45, True), (16, 0, False),     # 10-11
                       (18, 59, False), (19, 0, True), (19, 59, True), (20, 0, False)]:    # 14-15
        assert _in_window(datetime(*d, h, m, tzinfo=UTC)) is want, (h, m)


def test_windows_in_summer_shift_one_hour():
    d = (2026, 7, 8)
    assert _in_window(datetime(*d, 7, 0, tzinfo=UTC)) is True                              # 03:00 EDT
    assert _in_window(datetime(*d, 8, 30, tzinfo=UTC)) is False                            # شتاءً داخلها، صيفاً لا
    assert _in_window(datetime(*d, 14, 0, tzinfo=UTC)) is True
    assert _in_window(datetime(*d, 18, 30, tzinfo=UTC)) is True


def test_dst_change_days():
    assert _in_window(datetime(2026, 10, 31, 14, 30, tzinfo=UTC)) is True                  # قبل تغيير 1 نوفمبر
    assert _in_window(datetime(2026, 11, 2, 14, 30, tzinfo=UTC)) is False                  # بعده
    assert _in_window(datetime(2026, 11, 2, 15, 30, tzinfo=UTC)) is True


def test_every_template_condition_is_supported_and_listed_in_builder():
    for t in T.all_templates():
        for g in t["groups"]:
            for c in g["conditions"]:
                assert c["type"] in E.SUPPORTED_CONDITION_TYPES, (t["key"], c["type"])
                assert f'"{c["type"]}"' in FRONT, (t["key"], c["type"])                    # يظهر ويُعدَّل بالمنشئ بعد النسخ


def test_keys_unique_and_values_match_side():
    ts = T.all_templates()
    assert len({t["key"] for t in ts}) == len(ts)
    for t in ts:
        vals = [c["value"] for g in t["groups"] for c in g["conditions"] if c["value"]]
        wrong = ("هابط", "علاوة") if t["side"] == "BUY" else ("صاعد", "خصم")
        assert vals and not any(v in wrong for v in vals), t["key"]


def test_silver_bullet_requires_window_sweep_structure_and_fvg_only():
    t = T.get_template("nas_silver_bullet_buy")
    assert t["symbols"] == ["NAS100"] and t["timeframes"] == ["15m"]
    logic = {g["name"]: (g["logic"], [c["type"] for c in g["conditions"]]) for g in t["groups"]}
    assert logic["نافذة الطلقة الفضية"] == ("AND", ["silverbullet"])
    assert logic["سحب السيولة"] == ("AND", ["liquidity"])
    assert logic["منطقة الدخول"] == ("AND", ["fvg_retrace"])                               # لا Order Block
    assert t["min_score"] == 6 + 18 + 18 + 18                                             # العتبة = أقل إعداد مكتمل


def test_new_markets_exist_for_both_sides():
    syms = {s: 0 for s in ("NAS100", "BTC/USD", "USOIL", "EUR/USD")}
    for t in T.all_templates():
        for s in t["symbols"]:
            if s in syms:
                syms[s] += 1
    assert all(n >= 2 for n in syms.values()), syms


def test_gold_market_note_only_on_october_gold_families():
    orig = dict(T._TEST_RESULTS)
    T._TEST_RESULTS["nas_trend_buy"] = {"status": "testing", "days": 45, "trades": 1, "net_r": 0.1}
    try:
        assert T.get_template("nas_trend_buy")["test_note"] is None                        # لا "الذهب كان هابطاً" تحت ناسداك
    finally:
        T._TEST_RESULTS.clear()
        T._TEST_RESULTS.update(orig)
    assert T.get_template("gold_session_sell")["test_note"] == T.TEST_MARKET_NOTE


def _bars(rows):
    import pandas as pd
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"])


# فجوة صاعدة عند الشمعة 2 بين 101 و103، والأخيرة تعود إليها
_GAP_UP = [(100, 101, 99, 100.5), (101, 102, 100.5, 101.5), (103.5, 106, 103, 105), (105, 106, 104, 104.5), (104, 104.5, 102, 102.5)]


def test_retrace_detects_price_back_inside_recent_gap_both_sides():
    from app.services.ict_engine import ict_engine
    assert ict_engine._fvg_retrace(_bars(_GAP_UP)) == {"bullish": True, "bearish": False}
    mirror = [(200 - o, 200 - l, 200 - h, 200 - c) for o, h, l, c in _GAP_UP]
    assert ict_engine._fvg_retrace(_bars(mirror)) == {"bullish": False, "bearish": True}


def test_retrace_rejects_broken_old_and_untouched_gaps():
    from app.services.ict_engine import ict_engine
    broken = _GAP_UP[:4] + [(104, 104.5, 99, 100), (100, 102.5, 100, 102)]                  # أُغلقت تحت الفجوة ثم عادت
    assert ict_engine._fvg_retrace(_bars(broken))["bullish"] is False
    far = _GAP_UP[:3] + [(105, 106, 104.5, 105.5)]                                          # السعر لم يعد إليها
    assert ict_engine._fvg_retrace(_bars(far))["bullish"] is False
    pad = [(104, 105, 102, 104.5)] * 12                                                     # قاع 102 لا يصنع فجوة جديدة مع الشمعة 1
    old = _GAP_UP[:3] + pad + [(104, 104.5, 102, 102.5)]                                    # أقدم من 3 ساعات
    assert ict_engine._fvg_retrace(_bars(old))["bullish"] is False


def test_engine_fvg_fields_unchanged_and_old_flag_still_never_true():
    """المحرك لا يتغير: retrace مفتاح إضافي، والخلل القديم موثّق هنا حتى يقرر المالك."""
    from app.services.ict_engine import ict_engine
    a = ict_engine.detect_fvg(_bars(_GAP_UP))
    assert set(a) == {"bullish_fvgs", "bearish_fvgs", "in_bullish_fvg", "in_bearish_fvg", "nearest_bullish", "nearest_bearish", "retrace"}
    assert a["retrace"]["bullish"] is True and a["in_bullish_fvg"] is False                # السعر داخل الفجوة، والحقل القديم يقول لا
    assert a["bullish_fvgs"] == []                                                          # حُذفت كمملوءة، وهذا سبب الخلل
    an = {"fvg": a}                                                                         # الشرط يقرأ من التحليل الكامل
    assert E.SUPPORTED_CONDITION_TYPES["fvg"](an, "صاعد") is False
    assert E.SUPPORTED_CONDITION_TYPES["fvg_retrace"](an, "صاعد") is True
    assert E.SUPPORTED_CONDITION_TYPES["fvg_retrace"](an, "هابط") is False


def test_new_shadow_templates_start_after_they_were_fixed():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.database import Base
    from app.models.shadow_signal import ShadowSignal
    from app.services import template_shadow as S
    assert all(T.get_template(k) for k in S.SHADOW_TEMPLATES)                              # لا مفتاح قديم أو خاطئ
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng, tables=[ShadowSignal.__table__])
    db = sessionmaker(bind=eng)()

    def tr(day):
        t = datetime(2026, 11, day, 10, tzinfo=UTC)
        return {"time": t.isoformat(), "exit_time": (t + timedelta(hours=2)).isoformat(), "side": "BUY", "entry": 100.0, "sl": 99.0,
                "tp1": 101.0, "tp2": 102.0, "result": "TP2", "r": 1.2}
    assert S.save_trades(db, "nas_silver_bullet_buy", "NAS100", [tr(3)]) == 0              # قبل التثبيت: عينة رأيناها
    assert S.save_trades(db, "nas_silver_bullet_buy", "NAS100", [tr(5)]) == 1
    assert S.save_trades(db, "gold_session_sell", "XAU/USD", [tr(3)]) == 1                 # القديمة بتاريخها كما كانت


NOW = datetime(2026, 11, 3, 12, tzinfo=UTC)


def _tr(days_ago, r):
    return {"time": (NOW - timedelta(days=days_ago)).isoformat(), "r": r}


def _good(n=24):
    return [_tr(1 + i * 40 / n, 1.0 if i % 3 else -0.5) for i in range(n)]


def test_judge_passes_when_all_four_hold():
    j = D.judge(_good(), NOW)
    assert j["status"] == "tested" and j["trades"] == 24 and j["net_r"] > 0 and j["net_r_30"] > 0


def test_judge_too_few_trades_is_testing_not_tested():
    assert D.judge(_good(19), NOW)["status"] == "testing"


def test_judge_negative_on_45_days():
    assert D.judge([_tr(i + 1, -1.0) for i in range(25)], NOW)["status"] == "negative"


def test_judge_positive_45_but_negative_30_is_not_tested():
    ts = [_tr(40, 10.0)] + [_tr(1 + i, -0.1) for i in range(24)]
    j = D.judge(ts, NOW)
    assert j["net_r"] > 0 and j["net_r_30"] < 0 and j["status"] == "testing"


def test_judge_deep_drawdown_is_not_tested():
    ts = [_tr(44 - i, 2.0) for i in range(8)] + [_tr(35 - i, -1.0) for i in range(7)] + [_tr(25 - i, 1.0) for i in range(15)]
    j = D.judge(ts, NOW)
    assert j["max_dd_r"] == 7.0 and j["status"] == "testing"


def test_judge_needs_most_weeks_positive():
    ts = []
    for w in range(6):
        ts += [_tr(2 + w * 7 + i * 0.1, (9.0 if w == 0 else -0.2)) for i in range(5)]
    j = D.judge(ts, NOW)
    assert j["net_r"] > 0 and j["weeks_won"] <= j["weeks"] / 2 and j["status"] != "tested"


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
