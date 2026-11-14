"""
تصويت تيليجرام من البوت (2026-11-14) — services/bot_polls: التحقق من المدخلات، تسجيل الإجابة وسحبها، فصل تجربة الأدمن،
والعدّ بالفئة. قاعدة SQLite بالذاكرة لجداول التصويت وحدها.

  cd backend && python tests/test_bot_polls.py      (أو pytest)
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@127.0.0.1:1/x")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.database import Base  # noqa: E402
from app.models.bot_poll import BotPoll, BotPollAnswer, BotPollMessage  # noqa: E402
from app.services import bot_polls as BP  # noqa: E402


def _db():
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng, tables=[BotPoll.__table__, BotPollMessage.__table__, BotPollAnswer.__table__])
    return sessionmaker(bind=eng)()


def test_validate():
    assert BP.validate("  سؤال ", ["أ", " ب ", ""]) == ("سؤال", ["أ", "ب"])
    for q, o in [("", ["أ", "ب"]), ("س", ["أ"]), ("س", ["أ"] * 2), ("س", ["x" * 101, "ب"]), ("x" * 301, ["أ", "ب"]),
                 ("س", [str(i) for i in range(11)])]:
        try:
            BP.validate(q, o)
            raise AssertionError((q, o))
        except ValueError:
            pass


def test_answers_by_tier_and_test_excluded():
    db = _db()
    p = BotPoll(question="س", options=["أ", "ب", "ج"], audience="all")
    db.add(p)
    db.commit()
    for ptg, tid, tier in [("p1", "1", "paid"), ("p2", "2", "paid"), ("p3", "3", "trial"), ("pt", "9", "test")]:
        db.add(BotPollMessage(poll_id=p.id, poll_tg_id=ptg, telegram_id=tid, tier=tier))
    db.commit()
    assert BP.record_answer(db, "unknown", "1", [0]) == {"survey": False}          # تحدّي اليوم
    r = BP.record_answer(db, "p1", "1", [0])
    assert r["survey"] and r["first"] and r["thanks"]
    assert BP.record_answer(db, "p1", "1", [1])["first"] is False                  # تغيير الرأي = تحديث لا إضافة
    BP.record_answer(db, "p2", "2", [1])
    BP.record_answer(db, "p3", "3", [2])
    assert BP.record_answer(db, "pt", "9", [0])["thanks"] is None                  # تجربة الأدمن بلا شكر
    t = BP.results(db, p)["tally"]
    assert t["all"]["voters"] == 3 and t["all"]["counts"] == [0, 2, 1]
    assert t["paid"]["counts"] == [0, 2, 0] and t["paid"]["pct"] == [0, 100, 0]
    assert t["trial"]["counts"] == [0, 0, 1]
    assert BP.results(db, p)["sent_by_tier"] == {"paid": 2, "trial": 1}
    assert BP.record_answer(db, "p3", "3", [])["retracted"]                         # سحب التصويت
    assert BP.results(db, p)["tally"]["trial"]["voters"] == 0


def test_tally_multiple_choice():
    t = BP.tally(["أ", "ب"], [("paid", [0, 1]), ("trial", [0]), ("test", [1])])
    assert t["all"]["voters"] == 2 and t["all"]["counts"] == [2, 1] and t["all"]["pct"] == [100, 50]


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
