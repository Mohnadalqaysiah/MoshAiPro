"""
اختبارات آراء العملاء من البوت (2026-10-24) — خطوات البوت (review_flow)، شروط الإرسال، والنشر بالقناة عند الاعتماد مرة واحدة.

  cd backend && python tests/test_bot_reviews.py      (أو pytest)
"""
import os
import sys
import types
from datetime import datetime, timedelta, timezone
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

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import review_flow as RF  # noqa: E402
from app.database import Base  # noqa: E402
from app.models.payment import Payment, PaymentPlan, PaymentStatus  # noqa: E402
from app.models.review import Review  # noqa: E402
from app.models.user import PlanType, User  # noqa: E402

NOW = datetime.now(timezone.utc)


# ─── خطوات البوت ─────────────────────────────────────────────────────────────
def test_flow_full_path_with_photo():
    f = RF.ReviewFlow()
    f.start(1)
    assert f.on_rating(1, 6) is None and f.step(1) == "rating"          # خارج 1–5
    assert "صورة" in f.on_rating(1, 5)
    ok, txt = f.on_media(1, "photo", "FILE123")
    assert ok and "5–600" in txt                                          # مع وسائط يكفي 5 أحرف
    ok, txt = f.on_text(1, "ممتاز")
    assert ok and f.step(1) == "consent"
    p = f.on_consent(1, anonymous=True)
    assert p == {"rating": 5, "text": "ممتاز", "media_type": "photo", "media_file_id": "FILE123",
                 "anonymous": True, "consent": True}
    assert not f.active(1)


def test_flow_skip_media_needs_20_chars_and_rejects_big_video():
    f = RF.ReviewFlow()
    f.start(2)
    f.on_rating(2, 4)
    ok, txt = f.on_media(2, "video", "V", size_bytes=25 * 1024 * 1024)
    assert not ok and "20" in txt and f.step(2) == "media"
    assert "20–600" in f.on_skip(2)
    ok, txt = f.on_text(2, "قصير")
    assert not ok and f.step(2) == "text"
    ok, _ = f.on_text(2, "تجربة جيدة جداً والإشارات واضحة")
    assert ok
    assert f.on_consent(2, anonymous=False)["media_type"] is None


def test_flow_ignores_out_of_order_and_cancel():
    f = RF.ReviewFlow()
    assert f.on_consent(3, False) is None
    f.start(3)
    assert f.on_text(3, "x" * 30) == (False, None)                        # النص قبل النجوم يُتجاهل
    assert f.cancel(3) == RF.CANCELLED and not f.active(3)


# ─── الباكيند: الشروط ────────────────────────────────────────────────────────
def _db(paid_days_ago=None, full_name="سارة محمد"):
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng, tables=[User.__table__, Payment.__table__, Review.__table__])
    s = sessionmaker(bind=eng)()
    s.add(User(id=1, email="u@x.com", full_name=full_name, telegram_id="777", is_active=True, plan=PlanType.MONTHLY))
    if paid_days_ago is not None:
        s.add(Payment(user_id=1, plan=PaymentPlan.MONTHLY, amount_usd=30, tx_id="tx1", status=PaymentStatus.APPROVED,
                      created_at=NOW - timedelta(days=paid_days_ago)))
    s.commit()
    return s


def _submit(s, **kw):
    from app.api.reviews import upsert_bot_review
    args = dict(rating=5, text="تجربة ممتازة والإشارات واضحة جداً", media_type=None, media_file_id=None,
                anonymous=False, consent=True)
    args.update(kw)
    return upsert_bot_review(s, s.query(User).first(), **args)


def test_eligibility_same_as_web():
    assert "7 أيام" in _submit(_db(None))["error"]                       # لم يدفع
    assert "بعد" in _submit(_db(3))["error"]                             # دفع قبل 3 أيام
    assert _submit(_db(10))["ok"]


def test_saved_pending_with_media_and_names():
    s = _db(10)
    assert _submit(s, media_type="video", media_file_id="VID", text="رائع!")["ok"]
    r = s.query(Review).first()
    assert (r.status, r.via, r.media_type, r.media_file_id, r.display_name) == ("pending", "bot", "video", "VID", "سارة م.")
    assert _submit(s, anonymous=True)["ok"]                               # رأي واحد يُستبدل ويعود للمراجعة
    r = s.query(Review).first()
    assert s.query(Review).count() == 1 and r.display_name == "مشترك Qaffel" and r.media_type is None


def test_validation():
    s = _db(10)
    assert not _submit(s, text="قصير")["ok"]                             # بلا وسائط: 20 حرفاً
    assert not _submit(s, consent=False)["ok"]
    assert not _submit(s, rating=0)["ok"]
    assert not _submit(s, media_type="audio", media_file_id="A", text="قصير")["ok"]   # نوع غير مقبول = بلا وسائط


# ─── النشر بالقناة ───────────────────────────────────────────────────────────
class _Resp:
    def __init__(self, code=200, js=None):
        self.status_code, self._js = code, js or {"ok": True}

    def json(self):
        return self._js


def test_caption_escaped_and_channel_methods():
    import app.api.admin as A
    r = SimpleNamespace(rating=4, display_name="<b>x</b>", text="جيد & <script>", source="member",
                        admin_reply=None, media_type="photo", media_file_id="P1")
    cap = A._review_caption(r)
    assert "⭐⭐⭐⭐" in cap and "&lt;script&gt;" in cap and "&lt;b&gt;x" in cap and "موثّق" in cap
    calls = []
    orig = A.requests.post
    A.requests.post = lambda url, data=None, json=None, timeout=None: calls.append((url, data or json)) or _Resp()
    try:
        assert A._post_review_to_channel(r, "T") is None
        r.media_type, r.media_file_id = None, None
        assert A._post_review_to_channel(r, "T") is None
        A.requests.post = lambda *a, **k: _Resp(400, {"description": "Bad Request: chat not found"})
        assert "chat not found" in A._post_review_to_channel(r, "T")
    finally:
        A.requests.post = orig
    assert calls[0][0].endswith("/sendPhoto") and calls[0][1]["photo"] == "P1" and calls[0][1]["chat_id"] == "@QaffelPlatform"
    assert calls[1][0].endswith("/sendMessage")


def test_moderate_posts_to_channel_once():
    import app.api.admin as A
    s = _db(10)
    _submit(s)
    rid = s.query(Review).first().id
    posted = []
    o_post, o_tok = A._post_review_to_channel, A._get_bot_token
    A._post_review_to_channel = lambda r, token: posted.append(r.id) or None
    A._get_bot_token = lambda db: "T"
    try:
        res = A.admin_moderate_review(rid, A.ReviewModerateIn(status="approved"), admin=None, db=s)
        assert res["channel"] == "posted"
        res = A.admin_moderate_review(rid, A.ReviewModerateIn(status="approved", admin_reply="شكراً"), admin=None, db=s)
        assert res["channel"] is None and posted == [rid]                  # حفظ الرد لا يعيد النشر
        A._post_review_to_channel = lambda r, token: "chat not found"
        _submit(s, text="تعديل الرأي بعد أسبوع من الاستخدام")              # تعديل ← يعود للمراجعة ويُسمح بنشر جديد
        res = A.admin_moderate_review(rid, A.ReviewModerateIn(status="approved"), admin=None, db=s)
        assert res["channel"].startswith("failed") and s.query(Review).first().status == "approved"   # الاعتماد يبقى
    finally:
        A._post_review_to_channel, A._get_bot_token = o_post, o_tok


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
