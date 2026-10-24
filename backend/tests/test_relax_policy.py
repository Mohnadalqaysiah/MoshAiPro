"""
اختبارات التخفيف الجزئي لفلتر "بيع في منطقة خصم" (2026-10-24، قرار المالك) — services/relax_policy.py ونقاط المحرك الأربع.

  cd backend && python tests/test_relax_policy.py      (أو pytest)
"""
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

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.database import Base  # noqa: E402
from app.models.signal import Signal, SignalStatus, SignalType  # noqa: E402
from app.services import relax_policy as R  # noqa: E402
from app.services.ai_engine_v5 import mosh_ai_engine_v5 as ENG  # noqa: E402

settings = get_settings()   # lru_cache — نفس الكائن الذي يقرأه relax_policy


def _with_tfs(value, fn):
    old = settings.RELAX_SELL_IN_DISCOUNT_TFS
    settings.RELAX_SELL_IN_DISCOUNT_TFS = value
    try:
        return fn()
    finally:
        settings.RELAX_SELL_IN_DISCOUNT_TFS = old


# ─── الخطوة 7 (_zone_veto) ───────────────────────────────────────────────────
def test_default_relaxes_15m_and_1h_only():
    assert settings.RELAX_SELL_IN_DISCOUNT_TFS == "15m,1h"
    assert R.allows_sell_in_discount("15m") and R.allows_sell_in_discount("1h")
    assert not R.allows_sell_in_discount("4h") and not R.allows_sell_in_discount("1d")


def test_zone_veto_sell_in_discount_by_timeframe():
    for tf in ("15m", "1h"):
        a = {}
        assert ENG._zone_veto(a, "SELL", "BUY", "EURUSD", tf) is None          # لا رفض
        assert a["relaxed_rule"] == "SELL_IN_DISCOUNT" and a["zone_conflict_warning"] == "SELL_IN_DISCOUNT_ZONE"
    a = {"levels": {"entry": 1}}
    r = ENG._zone_veto(a, "SELL", "BUY", "EURUSD", "4h")                       # 4h: الفلتر باقٍ
    assert r is not None and r["rejection_reason"] == "ZONE_CONFLICT_SELL_IN_DISCOUNT" and "relaxed_rule" not in r
    assert r["_pre_reject_rec"] == "SELL"                                       # يبقى يُسجَّل بالظل كما كان


def test_zone_veto_unchanged_for_buy_in_premium_and_no_conflict():
    r = ENG._zone_veto({}, "BUY", "SELL", "EURUSD", "15m")
    assert r["rejection_reason"] == "ZONE_CONFLICT_BUY_IN_PREMIUM" and "relaxed_rule" not in r
    a = {}
    assert ENG._zone_veto(a, "SELL", "SELL", "EURUSD", "15m") is None and "relaxed_rule" not in a
    assert ENG._zone_veto(a, "BUY", None, "EURUSD", "15m") is None and "relaxed_rule" not in a


def test_switch_off_restores_filter_everywhere():
    """الرجوع الفوري: إعداد فارغ ← الفلتر كما كان على كل الأطر."""
    def run():
        r = ENG._zone_veto({}, "SELL", "BUY", "EURUSD", "15m")
        return r is not None and r["rejection_reason"] == "ZONE_CONFLICT_SELL_IN_DISCOUNT"
    assert _with_tfs("", run)


# ─── بوابة السلامة (Rule 2/6/7) ─────────────────────────────────────────────
def _sell(sym="EURUSD", flag=True, conf=70, entry=1.1, sl=1.102, tp1=1.097, rr=1.5):
    a = {"recommendation": "SELL", "levels": {"entry": entry, "stop_loss": sl, "tp1": tp1, "tp2": tp1},
         "gate_rr": rr, "ai_confidence_score": conf, "premium_discount": {"zone": "DISCOUNT", "bias": "BUY"},
         "market_structure": {"trend": "BEARISH"}, "gate_htf_aligned": True}
    if flag:
        a["relaxed_rule"] = "SELL_IN_DISCOUNT"
    return a


BEAR = {"market_structure": {"trend": "BEARISH"}}


def test_gate_blocks_untagged_and_passes_tagged():
    r = ENG._output_safety_gate(_sell(flag=False), "EURUSD", "1h", BEAR)
    assert r["recommendation"] == "WAIT" and r["safety_gate_reason"] == "DISCOUNT_ZONE_FORBIDS_SELL"
    r = ENG._output_safety_gate(_sell(), "EURUSD", "1h", BEAR)
    assert r["recommendation"] == "SELL" and r.get("safety_gate_passed")


def test_gate_gold_rules_6_and_7_respect_tag():
    g = dict(entry=4150.0, sl=4160.0, tp1=4135.0)
    r = ENG._output_safety_gate(_sell("XAUUSD", flag=False, **g), "XAUUSD", "1h", BEAR)
    assert r["recommendation"] == "WAIT"
    r = ENG._output_safety_gate(_sell("XAUUSD", **g), "XAUUSD", "1h", BEAR)
    assert r["recommendation"] == "SELL", r.get("safety_gate_reason")


def test_tag_does_not_bypass_other_rules():
    """الوسم يتجاوز فحص المنطقة وحده: اتجاه HTF المعاكس والثقة المنخفضة ما زالا يمنعان."""
    r = ENG._output_safety_gate(_sell(), "EURUSD", "1h", {"market_structure": {"trend": "BULLISH"}})
    assert r["recommendation"] == "WAIT" and r["safety_gate_reason"] == "HTF_BULLISH_FORBIDS_SELL"
    r = ENG._output_safety_gate(_sell(conf=40), "EURUSD", "1h", BEAR)
    assert r["recommendation"] == "WAIT" and "CONFIDENCE_TOO_LOW" in r["safety_gate_reason"]
    buy = {"recommendation": "BUY", "levels": {"entry": 1.1, "stop_loss": 1.098, "tp1": 1.103}, "gate_rr": 1.5,
           "ai_confidence_score": 70, "premium_discount": {"zone": "PREMIUM"}, "relaxed_rule": "SELL_IN_DISCOUNT"}
    r = ENG._output_safety_gate(buy, "EURUSD", "1h", {"market_structure": {"trend": "BULLISH"}})
    assert r["recommendation"] == "WAIT" and r["safety_gate_reason"] == "PREMIUM_ZONE_FORBIDS_BUY"


# ─── التعارض مع صفقة منصة نشطة ───────────────────────────────────────────────
def _db(rows):
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng, tables=[Signal.__table__])
    s = sessionmaker(bind=eng)()
    now = datetime.now(timezone.utc)
    for i, (mkt, side, status, exp_h) in enumerate(rows, start=1):
        s.add(Signal(id=i, user_id=1, market=mkt, timeframe="1h", signal_type=side, status=status,
                     entry_price=1, stop_loss=1, take_profit_1=1, take_profit_2=1, ai_confidence=70, signal_hash=f"h{i}",
                     expires_at=now + timedelta(hours=exp_h)))
    s.commit()
    return s


def test_should_drop_only_on_active_opposite_same_market():
    tagged = {"relaxed_rule": "SELL_IN_DISCOUNT", "recommendation": "SELL"}
    assert R.should_drop(_db([("EURUSD", SignalType.BUY, SignalStatus.ACTIVE, 5)]), tagged, "EURUSD")
    assert not R.should_drop(_db([("EURUSD", SignalType.SELL, SignalStatus.ACTIVE, 5)]), tagged, "EURUSD")  # نفس الاتجاه
    assert not R.should_drop(_db([("GBPUSD", SignalType.BUY, SignalStatus.ACTIVE, 5)]), tagged, "EURUSD")   # رمز آخر
    assert not R.should_drop(_db([("EURUSD", SignalType.BUY, SignalStatus.ACTIVE, -1)]), tagged, "EURUSD")  # منتهية
    assert not R.should_drop(_db([("EURUSD", SignalType.BUY, SignalStatus.SL_HIT, 5)]), tagged, "EURUSD")   # مغلقة
    untagged = {"recommendation": "SELL"}                                       # غير الموسوم لا يُمس أبداً
    assert not R.should_drop(_db([("EURUSD", SignalType.BUY, SignalStatus.ACTIVE, 5)]), untagged, "EURUSD")


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
