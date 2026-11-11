"""
"📸 شارك نتيجتك" + إشعار المالك بالآراء (2026-11-11).

  cd backend && python tests/test_result_share.py      (أو pytest)
"""
import os
import sys
import types
from datetime import datetime, timezone
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
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.database as Dd  # noqa: E402
import result_share_flow as RS  # noqa: E402
from app.models.result_share import ResultShare  # noqa: E402
from app.models.review import Review  # noqa: E402
from app.models.user import PlanType, User  # noqa: E402
from app.services import result_shares as SV  # noqa: E402


def test_flow_photo_then_consent():
    f = RS.ShareFlow()
    assert "لقطة شاشة" in f.start(1)
    assert f.on_image(1, "video", "V") == (False, RS.ONLY_PHOTO)
    assert f.on_consent(1, "rs_c_name") is None                                   # قبل الصورة
    ok, txt = f.on_image(1, "photo", "P1", "  ربح الذهب  ")
    assert ok and txt == RS.ASK_CONSENT and f.hint(1) == RS.PICK_CONSENT
    assert f.on_image(1, "photo", "P2") == (False, RS.PICK_CONSENT)               # صورة ثانية بخطوة الموافقة
    assert f.on_consent(1, "rs_c_bad") is None
    assert f.on_consent(1, "rs_c_private") == {"file_kind": "photo", "file_id": "P1", "caption": "ربح الذهب",
                                               "consent": "private"}
    assert not f.active(1)


def test_flow_english_and_cancel():
    f = RS.ShareFlow()
    assert "screenshot" in f.start(2, "en")
    ok, _ = f.on_image(2, "document", "D1")
    assert ok and f.on_consent(2, "rs_c_anon")["file_kind"] == "document"
    f.start(3)
    assert f.cancel(3) == RS.CANCELLED and not f.active(3)


def _db():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Dd.Base.metadata.create_all(eng, tables=[User.__table__, ResultShare.__table__, Review.__table__])
    S = sessionmaker(bind=eng)
    s = S()
    s.add(User(id=1, email="a@x.com", password_hash="x", telegram_id="777", plan=PlanType.MONTHLY))
    s.commit()
    Dd.SessionLocal = S
    return S


def _share(s, **kw):
    d = {"telegram_id": "777", "username": "sara", "name": "سارة", "file_kind": "photo", "file_id": "F",
         "caption": "ربح <3R>", "consent": "name"}
    d.update(kw)
    return SV.record_share(s, d)


def test_record_validates_links_user_and_caps_daily():
    S = _db()
    s = S()
    assert not _share(s, file_kind="video")["ok"] and not _share(s, consent="x")["ok"]
    r = _share(s)
    assert r["ok"] and s.query(ResultShare).get(r["id"]).user_id == 1
    assert _share(s, telegram_id="999")["ok"] and s.query(ResultShare).filter_by(telegram_id="999").one().user_id is None
    for _ in range(SV.DAILY_MAX - 1):
        assert _share(s)["ok"]
    assert "حد اليومي" in _share(s)["error"]
    s.close()


def test_owner_gets_the_photo_with_identity_and_consent():
    S = _db()
    s = S()
    rid = _share(s)["id"]
    did = _share(s, file_kind="document", telegram_id="999", username="", consent="private")["id"]
    s.close()
    calls = []

    class _R:
        ok, text = True, ""

    o_post, o_settings, o_token = SV.requests.post, None, None
    import app.config as C
    import app.services.admin_notify as AN
    o_settings, o_token = C.get_settings, AN.get_bot_token
    SV.requests.post = lambda url, json=None, timeout=0: calls.append((url, json)) or _R()
    C.get_settings = lambda: SimpleNamespace(ADMIN_TELEGRAM_ID="42")
    AN.get_bot_token = lambda: "TOKEN"
    try:
        SV.send_to_owner(rid)
        SV.send_to_owner(did)
    finally:
        SV.requests.post, C.get_settings, AN.get_bot_token = o_post, o_settings, o_token
    (u1, j1), (u2, j2) = calls
    assert u1.endswith("/sendPhoto") and j1["photo"] == "F" and j1["chat_id"] == "42"
    assert "@sara" in j1["caption"] and "a@x.com" in j1["caption"] and "تُنشر باسمه" in j1["caption"]
    assert "&lt;3R&gt;" in j1["caption"]                                             # HTML آمن
    assert u2.endswith("/sendDocument") and "غير مربوط" in j2["caption"] and "للفريق فقط" in j2["caption"]
    s = S()
    assert all(x.sent_to_owner_at for x in s.query(ResultShare).all())
    s.close()


def test_owner_notified_of_new_review():
    S = _db()
    s = S()
    s.add(Review(id=5, user_id=1, source="user", rating=4, text="منصة <جيدة>", display_name="سارة م.", via="bot",
                 media_type="photo", status="pending", consent_public=True, created_at=datetime.now(timezone.utc)))
    s.commit()
    s.close()
    import app.api.reviews as RV
    import app.services.admin_notify as AN
    sent = []
    o = AN.notify_admin_telegram
    AN.notify_admin_telegram = sent.append
    try:
        RV.notify_new_review(5)
    finally:
        AN.notify_admin_telegram = o
    assert len(sent) == 1 and "بانتظار موافقتك" in sent[0] and "مستخدم" in sent[0] and "📷" in sent[0]
    assert "&lt;جيدة&gt;" in sent[0] and "a@x.com" in sent[0]


def test_bot_wiring():
    src = (ROOT.parent / "telegram-bot" / "bot.py").read_text(encoding="utf-8")
    assert src.count('callback_data="m_share"') == 2                                # بالقائمة العربية والإنجليزية
    assert 'CommandHandler("share", cmd_share)' in src and 'pattern=r"^(m_share|rs_)"' in src
    assert "filters.Document.IMAGE" in src and '"/api/v1/bot/result-share"' in src
    bot_api = (ROOT / "app" / "api" / "bot.py").read_text(encoding="utf-8")
    assert '@router.post("/result-share")' in bot_api and "notify_new_review" in bot_api
    rv = (ROOT / "app" / "api" / "reviews.py").read_text(encoding="utf-8")
    assert "background_tasks.add_task(notify_new_review" in rv


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
