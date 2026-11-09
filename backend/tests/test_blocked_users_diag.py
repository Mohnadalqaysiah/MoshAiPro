"""
اختبارات أداة "لماذا يحظرون البوت" (2026-11-09) — وقت الحظر المقدَّر، والحالة وقتها، وما سبقه.

  cd backend && python tests/test_blocked_users_diag.py      (أو pytest)
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import diag_blocked_users as D  # noqa: E402

T0 = datetime(2026, 10, 1, tzinfo=timezone.utc)
BLOCK = lambda e: "blocked" in (e or "")  # noqa: E731


def _user(**kw):
    base = dict(id=1, telegram_linked_at=T0, created_at=T0, trial_ends_at=T0 + timedelta(days=7))
    base.update(kw)
    return NS(**base)


def _rows(n_ok, fail_at_day, variant="full"):
    rows = [(T0 + timedelta(hours=6 * i), True, variant, None, 100 + i) for i in range(n_ok)]
    rows.append((T0 + timedelta(days=fail_at_day), False, "full", "Forbidden: bot was blocked by the user", 999))
    return rows


def test_not_blocked_returns_none():
    rows = [(T0, True, "full", None, 1), (T0 + timedelta(days=1), False, "full", "Timed out", 2)]
    assert D.block_profile(_user(), rows, {}, lambda u, t: False, [], BLOCK) is None   # فشل شبكة ليس حظراً


def test_block_during_trial_counts_messages_before_it():
    p = D.block_profile(_user(), _rows(8, 3), {}, lambda u, t: False, [], BLOCK)
    assert p["status"] == "أثناء التجربة" and p["bucket"] == "3–7 أيام" and p["received"] == 8
    assert round(p["per_day"], 2) == round(8 / 3, 2) and p["masked_share"] == 0 and p["returned"] is False


def test_after_trial_masked_and_losses_before_block():
    outcome = {100 + i: "SL_HIT" for i in range(40)}
    p = D.block_profile(_user(), _rows(40, 12, "masked"), outcome, lambda u, t: False, [], BLOCK)
    assert p["status"] == "بعد انتهاء التجربة" and p["bucket"] == "7–14 يوماً"
    assert p["masked_share"] == 1.0 and p["last5_sl"] == 5 and p["last5_known"] == 5


def test_paid_wins_over_trial_and_broadcast_window():
    bc = [T0 + timedelta(days=2, hours=12)]
    p = D.block_profile(_user(), _rows(4, 3), {}, lambda u, t: True, bc, BLOCK)
    assert p["status"] == "مدفوع" and p["after_broadcast"] is True
    far = D.block_profile(_user(), _rows(4, 3), {}, lambda u, t: False, [T0], BLOCK)
    assert far["after_broadcast"] is False                                            # أكثر من 48 ساعة قبله


def test_returned_after_block_and_same_day_bucket():
    rows = _rows(2, 0.5) + [(T0 + timedelta(days=4), True, "full", None, 7)]
    p = D.block_profile(_user(), rows, {}, lambda u, t: False, [], BLOCK)
    assert p["returned"] is True and p["bucket"] == "أقل من يوم"


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
