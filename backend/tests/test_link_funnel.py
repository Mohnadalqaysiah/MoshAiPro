"""
قمع ربط تيليجرام (2026-11-09): تسجيل ضغطات Start، وتذكير الربط بعد يوم، وشاشة "خطوة أخيرة".

  cd backend && python tests/test_link_funnel.py      (أو pytest)
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@127.0.0.1:1/x")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.database as Dd  # noqa: E402
from app.models.bot_start import BotStart  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402
from app.services import bot_starts as BS  # noqa: E402
from app.services import link_reminder as LR  # noqa: E402

NOW = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)


def _db():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Dd.Base.metadata.create_all(eng, tables=[User.__table__, BotStart.__table__])
    return sessionmaker(bind=eng)


def _u(i, hours, **kw):
    base = dict(id=i, email=f"u{i}@x.com", password_hash="x", created_at=NOW - timedelta(hours=hours),
                is_verified=True, is_active=True, notifications_enabled=True, language="ar")
    base.update(kw)
    return User(**base)


def test_bot_start_recorded_once_per_account_and_reports_linked():
    S = _db()
    s = S()
    s.add(_u(1, 5, telegram_id="777"))
    s.commit()
    assert BS.record_start(s, "555", "ar") == {"linked": False}
    assert BS.record_start(s, "555", "ar") == {"linked": False}
    assert BS.record_start(s, "777", "en") == {"linked": True}
    assert BS.record_start(s, "", "ar") == {"linked": False}
    rows = {r.telegram_id: r for r in s.query(BotStart).all()}
    assert set(rows) == {"555", "777"}
    assert rows["555"].starts == 2 and rows["555"].had_account is False
    assert rows["777"].had_account is True
    s.close()


def test_reminder_only_new_unlinked_verified_once():
    S = _db()
    s = S()
    s.add_all([
        _u(1, 30),                                   # يستحق ← إيميل
        _u(2, 30, telegram_id="9"),                  # مربوط
        _u(3, 10),                                   # أقل من يوم
        _u(4, 100),                                  # قديم — لا رسالة لقاعدة المستخدمين القديمة
        _u(5, 30, is_verified=False),                # بريد غير مؤكَّد
        _u(6, 30, notifications_enabled=False),      # أوقف الإشعارات ← يُوسم بلا إرسال
        _u(7, 30, language="en"),                    # له إشعار متصفح ← push لا إيميل
        _u(8, 30, role=UserRole.ADMIN),
    ])
    s.commit()
    mails, pushes = [], []

    def send_email(to, subject, body):
        mails.append((to, subject, body))
        return True

    def send_push(db, u, title, body, url="", tag=""):
        if u.id == 7:
            pushes.append((u.id, title, url))
            return 1
        return 0

    out = LR.process(s, NOW, bot_username="Qaffelbot", send_email=send_email, send_push=send_push)
    assert out == {"push": 1, "email": 1, "skipped": 1}
    assert [m[0] for m in mails] == ["u1@x.com"]
    tok = s.query(User).get(1).telegram_link_token
    assert tok and f"https://t.me/Qaffelbot?start={tok}" in mails[0][2]
    assert pushes == [(7, "One step left: link Telegram 📲", "/dashboard?link=telegram")]
    marked = {u.id for u in s.query(User).all() if u.telegram_link_reminded_at}
    assert marked == {1, 6, 7}
    assert LR.process(s, NOW + timedelta(hours=1), bot_username="Qaffelbot",
                      send_email=send_email, send_push=send_push) == {"push": 0, "email": 0, "skipped": 0}
    s.close()


def test_bot_and_shell_wiring():
    bot = (ROOT.parent / "telegram-bot" / "bot.py").read_text(encoding="utf-8")
    start = bot[bot.index("async def cmd_start("):bot.index("async def cmd_menu(")]
    assert '"/api/v1/bot/start-seen"' in start and "/register?utm_source=telegram_bot" in start
    assert 'seen.get("linked")' in start                                     # المربوط لا يُطلب منه الربط
    shell = (ROOT.parent / "frontend" / "src" / "components" / "AppShell.jsx").read_text(encoding="utf-8")
    assert "<TelegramLinkStep onClose={closeLinkStep} />" in shell and "{!linkStepOpen && <OnboardingTour />}" in shell
    main = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert "link_reminder_checker()" in main and "link_reminder_task.cancel()" in main


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
