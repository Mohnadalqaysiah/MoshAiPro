"""
اختبارات رسائل تيليجرام v2 (2026-10-19) — تنسيق الإشارات والنتائج والإحصائيات، ونتائج المنتهي اشتراكه،
وإعلان الصورة من اللوحة.

  cd backend && python tests/test_telegram_messages.py      (أو pytest)
"""
import asyncio
import os
import re
import sys
import types
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "telegram-bot"))
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@127.0.0.1:1/x")


class _Stub(types.ModuleType):
    def __getattr__(self, n):
        if n.startswith("__"):
            raise AttributeError(n)
        return type(n, (), {"__init__": lambda self, *a, **k: None})


for _m in ("telegram", "telegram.ext", "telegram.constants", "telegram.error"):
    sys.modules.setdefault(_m, _Stub(_m))

import messages as M  # noqa: E402

SIG = {"id": 7, "market": "XAUUSD", "signal_type": "SELL", "entry_price": 2400.0, "stop_loss": 2410.0,
       "take_profit_1": 2385.0, "take_profit_2": 2370.0, "trade_type": "SWING",
       "expires_at": "2026-10-19T20:00:00+00:00", "news_context": "بيانات <CPI> & الفائدة"}


def _balanced(html: str) -> bool:
    stack = []
    for close, tag in re.findall(r"<(/?)(b|i|code)>", html):
        if not close:
            stack.append(tag)
        elif not stack or stack.pop() != tag:
            return False
    return not stack


def test_r_of_signs():
    assert M.r_of(100, 90, 120, True) == 2.0
    assert M.r_of(100, 110, 85, False) == 1.5
    assert M.r_of(100, 100, 120, True) is None          # مخاطرة صفرية
    assert M.fmt_r(-1.0) == "−1.0R"


def test_signal_full_levels_and_escaping():
    t = M.signal_full(SIG, "الذهب", "4 ساعات", 78)
    assert "بيع الذهب" in t and ("2,400" in t or "2400" in t)
    assert "+1.5R" in t and "+3.0R" in t                 # (2400-2385)/10 ، (2400-2370)/10
    assert "&lt;CPI&gt; &amp;" in t                     # نص الأخبار مُهرَّب لـHTML
    assert _balanced(t)


def test_masked_hides_direction_and_levels():
    t = M.signal_masked(SIG, "الذهب", "4 ساعات")
    for word in ("شراء", "بيع", "BUY", "SELL", "2400", "2,400", "2410", "ثقة"):
        assert word not in t, word
    assert "للمشتركين" in t and "Qaffel" in t and _balanced(t)


def test_ago_arabic_plurals():
    from datetime import datetime, timedelta, timezone
    now = datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc)
    at = lambda m: (now - timedelta(minutes=m)).isoformat()  # noqa: E731
    assert M.ago(at(60), now) == "ساعة"
    assert M.ago(at(120), now) == "ساعتين"
    assert M.ago(at(480), now) == "8 ساعات"
    assert M.ago(at(11 * 60), now) == "11 ساعة"
    assert M.ago(at(8 * 60 + 30), now) == "8 ساعات و30 دقيقة"
    assert M.ago(at(5), now) == "5 دقائق"
    assert M.ago(at(3 * 1440), now) == "3 أيام"


def test_outcome_subscriber():
    o = {"status": "TP1_HIT", "signal_type": "SELL", "entry": 2400, "sl": 2410, "tp1": 2385, "tp2": 2370,
         "pnl_pct": 0.62, "created_at": "2026-10-19T08:00:00+00:00"}
    t = M.outcome_subscriber(o, "الذهب")
    assert "الهدف 1" in t and "+1.5R" in t and "الإغلاق" not in t and _balanced(t)
    sl = M.outcome_subscriber({**o, "status": "SL_HIT"}, "الذهب")
    assert "−1.0R" in sl and _balanced(sl)


def test_outcome_expired_win_detailed_loss_brief():
    o = {"status": "TP2_HIT", "signal_type": "BUY", "entry": 100, "sl": 90, "tp1": 110, "tp2": 125,
         "pnl_pct": 25.0, "created_at": "2026-10-19T08:00:00+00:00"}
    w = M.outcome_expired(o, "بيتكوين")
    assert "الهدف الثاني تحقق" in w and "+2.5R" in w and "<code>90" in w and "<code>100" in w   # المستويات ظاهرة
    assert "اشتراكك" in w and _balanced(w)
    lo = M.outcome_expired({**o, "status": "SL_HIT"}, "بيتكوين")
    assert "−1R" in lo and "الخاسرة" in lo and lo.count("\n") <= 2 and _balanced(lo) and "وقف الخسارة" in lo and "شفافية" in lo   # الخاسرة تصل، مختصرة
    be = M.outcome_expired({**o, "status": "BREAKEVEN"}, "بيتكوين")
    assert "0R" in be


def test_stats_card():
    empty = M.stats_card({"full_name": "سارة", "total_signals": 0})
    assert "لا صفقات مغلقة" in empty and _balanced(empty)
    st = {"full_name": "أ<ب>", "plan": "monthly", "plan_label": "شهري", "total_signals": 4, "wins": 3, "losses": 1,
          "win_rate": 75, "total_r": 2.5, "avg_r": 0.625, "best_r": 2.0, "worst_r": -1.0,
          "recent_trades": [{"market": "XAUUSD", "type": "BUY", "status": "TP1_HIT", "r": 1.5, "closed_at": "10/19"}]}
    t = M.stats_card(st, {"XAUUSD": "الذهب"})
    assert "+2.5R" in t and "▰" in t and "الذهب شراء" in t and "أ&lt;ب&gt;" in t and _balanced(t)


def test_channel_line_in_main_messages():
    """(2026-10-24) معرّف القناة العامة بكل الرسائل الرئيسية — والخاسرة للمنتهي اشتراكه تبقى مختصرة (الزر يكفي)."""
    o = {"status": "TP1_HIT", "signal_type": "SELL", "entry": 2400, "sl": 2410, "tp1": 2385, "tp2": 2370, "pnl_pct": 0.6}
    for t in (M.signal_full(SIG, "الذهب", "4 ساعات", 78), M.signal_masked(SIG, "الذهب", "4 ساعات"),
              M.outcome_subscriber(o, "الذهب"), M.outcome_expired(o, "الذهب"),
              M.stats_card({"full_name": "x", "total_signals": 0})):
        assert "@QaffelPlatform" in t and _balanced(t)
    assert "@QaffelPlatform" not in M.outcome_expired({**o, "status": "SL_HIT"}, "الذهب")


def test_teaser_gate_caps_channel_posts():
    from datetime import datetime, timedelta, timezone
    g = M.TeaserGate(daily_max=2, min_gap_min=60)
    t = datetime(2026, 10, 26, 8, 0, tzinfo=timezone.utc)
    assert g.allow("A", t)
    g.mark("A", t)
    assert not g.allow("A", t + timedelta(hours=3))                 # نفس القرار مرة واحدة
    assert not g.allow("B", t + timedelta(minutes=30))              # فاصل ساعة
    assert g.allow("B", t + timedelta(minutes=61))
    g.mark("B", t + timedelta(minutes=61))
    assert not g.allow("C", t + timedelta(hours=5))                 # الحد اليومي 2
    assert g.allow("C", t + timedelta(days=1))                      # يوم جديد
    assert not M.TeaserGate(daily_max=0).allow("X", t)              # 0 = النشر بالقناة متوقف


def test_expired_wants_result():
    from app.api.bot import _expired_wants_result as f
    u = lambda **k: SimpleNamespace(**{"notifications_enabled": True, "notify_watchlist": None, **k})  # noqa: E731
    assert f(u(), "XAUUSD")
    assert not f(u(notifications_enabled=False), "XAUUSD")
    assert f(u(notify_watchlist=["xauusd"]), "XAUUSD")
    assert not f(u(notify_watchlist=["BTCUSD"]), "XAUUSD")


# ─── إعلان الصورة ────────────────────────────────────────────────────────────
class _Resp:
    def __init__(self, code, js=None, text=""):
        self.status_code, self._js, self.text = code, js or {}, text

    def json(self):
        return self._js


def test_photo_upload_once_then_file_id(monkeypatch=None):
    import app.api.admin as A
    calls = []

    def fake_post(url, data=None, files=None, timeout=None):
        calls.append((data.copy(), files))
        return _Resp(200, {"result": {"photo": [{"file_id": "small"}, {"file_id": "BIG"}]}})
    orig, A.requests.post = A.requests.post, fake_post
    logs = []
    orig_log, A._update_broadcast_log = A._update_broadcast_log, lambda *a, **k: logs.append(a)
    try:
        A._photo_broadcast_task(["1", "2", "3"], "<b>x</b>", "T", b"img", "a.png", 9)
    finally:
        A.requests.post, A._update_broadcast_log = orig, orig_log
    assert calls[0][1] is not None and "photo" not in calls[0][0]       # الأول يرفع الملف
    assert all(c[1] is None and c[0]["photo"] == "BIG" for c in calls[1:])   # الباقي بـfile_id الأكبر
    assert logs[-1][1:3] == (3, 0)


def test_photo_html_fallback():
    import app.api.admin as A
    seen = []

    def fake_post(url, data=None, files=None, timeout=None):
        seen.append(data)
        if data.get("parse_mode"):
            return _Resp(400, text="Bad Request: can't parse entities")
        return _Resp(200, {"result": {"photo": [{"file_id": "F"}]}})
    orig, A.requests.post = A.requests.post, fake_post
    try:
        ok, fid = A._send_telegram_photo("1", "<b>a</b>", "T", photo_bytes=b"x")
    finally:
        A.requests.post = orig
    assert ok and fid == "F" and seen[-1]["caption"] == "a"


def test_photo_endpoint_validation():
    import app.api.admin as A
    from fastapi import HTTPException

    class _Up:
        def __init__(self, ct, data, name="a.png"):
            self.content_type, self._d, self.filename = ct, data, name

        async def read(self):
            return self._d
    orig, A._get_bot_token = A._get_bot_token, lambda db: "T"
    admin = SimpleNamespace(id=1, telegram_id=None)

    def run(up, msg="hi"):
        try:
            asyncio.run(A.send_telegram_photo(background=None, file=up, title=None, message=msg, test_to_me=True,
                                              user_ids=None, admin=admin, db=None))
        except HTTPException as e:
            return e.detail
    try:
        assert "صورة" in run(_Up("application/pdf", b"x"))
        assert "10" in run(_Up("image/png", b"x" * (A._PHOTO_MAX_BYTES + 1)))
        assert "1024" in run(_Up("image/png", b"x"), msg="ن" * 1100)
        assert "مربوط" in run(_Up("image/png", b"x"))       # تجربة بلا تيليجرام مربوط
    finally:
        A._get_bot_token = orig


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
