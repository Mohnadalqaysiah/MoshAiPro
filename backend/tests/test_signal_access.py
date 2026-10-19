"""
اختبار إغلاق ثغرة /signals/{id} (2026-10-19): كانت بلا مصادقة فتكشف اتجاه ومستويات كل إشارة نشطة لأي زائر.

  cd backend && python tests/test_signal_access.py      (أو pytest)
"""
import asyncio
import inspect
import os
import sys
import types
from datetime import datetime, timezone
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

import app.api.signals as S  # noqa: E402
from app.models.signal import SignalStatus, SignalType  # noqa: E402
from app.models.user import PlanType, UserRole  # noqa: E402
from app.services.auth_service import get_current_user  # noqa: E402

E = lambda v: SimpleNamespace(value=v)  # noqa: E731


def _sig(status=SignalStatus.ACTIVE, user_id=1):
    return SimpleNamespace(
        id=99, market="XAUUSD", timeframe="4h", user_id=user_id, entry_price=2400.0, stop_loss=2410.0,
        take_profit_1=2385.0, take_profit_2=2370.0, current_price=2398.0, ai_confidence=78, ai_reasoning="سبب",
        wyckoff_phase=None, premium_discount=None, killzone=None, risk_reward_ratio=1.5, profit_loss=None,
        profit_loss_percentage=None, created_at=datetime(2026, 10, 19, tzinfo=timezone.utc), expires_at=None,
        signal_type=E("SELL"), signal_quality=E("A"), status=status,
    )


class _Q:
    def __init__(self, result):
        self._r = result

    def filter(self, *a, **k):
        return self

    def first(self):
        return self._r


class _DB:
    """أول استعلام = جلب الإشارة، الثاني (إن وُجد) = هل للمستخدم نسخة منها."""
    def __init__(self, sig, own_copy=False):
        self._res = [sig, (1,) if own_copy else None]

    def query(self, *a):
        return _Q(self._res.pop(0) if self._res else None)


def _user(uid=2, plan=PlanType.TRIAL, role=UserRole.USER):
    return SimpleNamespace(id=uid, plan=plan, role=role)


def _get(sig, user, own_copy=False):
    return asyncio.run(S.get_signal_details(signal_id=99, user=user, db=_DB(sig, own_copy)))["data"]


def test_requires_login():
    dep = inspect.signature(S.get_signal_details).parameters["user"].default
    assert getattr(dep, "dependency", None) is get_current_user


def test_active_masked_for_non_subscriber():
    d = _get(_sig(), _user())
    assert d["locked"] is True
    for k in ("signal_type", "entry_price", "stop_loss", "take_profit_1", "take_profit_2", "ai_confidence", "ai_reasoning"):
        assert k not in d, k


def test_active_full_for_subscriber_admin_owner_and_trial_copy():
    for u in (_user(plan=PlanType.MONTHLY), _user(plan=PlanType.WEEKLY), _user(role=UserRole.ADMIN), _user(uid=1)):
        d = _get(_sig(), u)
        assert d["locked"] is False and d["entry_price"] == 2400.0
    d = _get(_sig(), _user(), own_copy=True)          # وصلته بحصة التجربة (صف باسمه بنفس المستويات)
    assert d["locked"] is False and d["stop_loss"] == 2410.0


def test_closed_visible_to_any_logged_in():
    for st in (SignalStatus.TP1_HIT, SignalStatus.SL_HIT, SignalStatus.BREAKEVEN, SignalStatus.EXPIRED):
        d = _get(_sig(status=st), _user())
        assert d["locked"] is False and d["entry_price"] == 2400.0


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
