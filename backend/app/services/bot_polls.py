"""
(2026-11-14) تصويت تيليجرام جماعي من البوت — المالك: "بدنا نرسل تصويت جماعي بالبوت كيف بيتم".

- لا يُرسل شيء إلا بضغطة الأدمن (لوحة الإدارة ← تصويت تيليجرام): إنشاء ← "جرّبه عليّ" ← "أرسل" (مرة واحدة لكل تصويت).
- الجمهور: paid (اشتراك ساري) / trial (تجربة نشطة أو منتهية) / all. يُستبعد من حظر البوت (telegram_reach) ومن أطفأ
  الإشعارات (قرار 09/11: الإيقاف يحترمه كل إرسال) والمحظورون والمعطّلون.
- تصويت تيليجرام أصلي غير مجهول (is_anonymous=False) ليصل poll_answer للبوت؛ يمرّره البوت إلى /bot/poll-answer فنربطه
  بالتصويت عبر poll_tg_id. أي poll_tg_id غير موجود هنا ← البوت يعامله كتحدّي اليوم كما كان.
- فئة المستلم تُحفظ لحظة الإرسال (BotPollMessage.tier) فتُقسم النتائج مدفوع/تجربة.
"""
import time
from datetime import datetime, timezone

import requests
from loguru import logger

AUDIENCES = ("paid", "trial", "all")
MAX_OPTIONS = 10
THANKS = "🙏 شكراً، وصل رأيك — يساعدنا نحسّن Qaffel لك."


def validate(question: str, options: list) -> tuple[str, list]:
    q = (question or "").strip()
    opts = [str(o).strip() for o in (options or []) if str(o).strip()]
    if not 1 <= len(q) <= 300:
        raise ValueError("السؤال من 1 إلى 300 حرف")
    if not 2 <= len(opts) <= MAX_OPTIONS:
        raise ValueError(f"من 2 إلى {MAX_OPTIONS} خيارات")
    if any(len(o) > 100 for o in opts):
        raise ValueError("كل خيار حتى 100 حرف")
    if len(set(opts)) != len(opts):
        raise ValueError("خيارات مكرّرة")
    return q, opts


def tier_label(user) -> str:
    from app.models.user import UserRole
    from app.services.signal_quota import tier_of
    if getattr(user, "role", None) == UserRole.ADMIN:
        return "admin"
    return "paid" if tier_of(user) == "full" else "trial"


def audience_users(db, audience: str):
    from sqlalchemy import or_
    from app.models.user import PlanType, User
    from app.services.telegram_reach import reachable
    users = db.query(User).filter(
        User.telegram_id.isnot(None), User.telegram_id != "", User.is_active == True,   # noqa: E712
        User.plan != PlanType.BANNED,
        or_(User.notifications_enabled.is_(None), User.notifications_enabled == True),  # noqa: E712 — NULL = مفعّلة
        reachable(),
    ).all()
    out = []
    for u in users:
        t = tier_label(u)
        if t == "admin":
            continue                      # الأدمن يجرّب بزر "جرّبه عليّ" ولا يُحتسب بالنتائج
        if audience == "all" or t == audience:
            out.append((u, t))
    return out


def send_one(token: str, chat_id: str, question: str, options: list, multiple: bool):
    """(ok, poll_tg_id, error)"""
    url = f"https://api.telegram.org/bot{token}/sendPoll"
    payload = {"chat_id": chat_id, "question": question, "options": options,
               "is_anonymous": False, "allows_multiple_answers": bool(multiple)}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 429:
            time.sleep(resp.json().get("parameters", {}).get("retry_after", 5))
            resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        if data.get("ok"):
            return True, str(data["result"]["poll"]["id"]), None
        return False, None, data.get("description") or f"HTTP {resp.status_code}"
    except Exception as e:  # شبكة
        return False, None, str(e)[:200]


def _record_message(db, poll_id, poll_tg_id, telegram_id, user_id, tier):
    from app.models.bot_poll import BotPollMessage
    db.add(BotPollMessage(poll_id=poll_id, poll_tg_id=poll_tg_id, telegram_id=str(telegram_id), user_id=user_id, tier=tier))


def send_test(db, poll, admin, token):
    if not admin.telegram_id:
        return False, "حسابك غير مربوط بتيليجرام"
    ok, ptg, err = send_one(token, admin.telegram_id, poll.question, poll.options, poll.allows_multiple)
    if ok:
        _record_message(db, poll.id, ptg, admin.telegram_id, admin.id, "test")
        db.commit()
    return ok, err


def send_task(poll_id: int, token: str):
    """إرسال بالخلفية بجلسة مستقلة؛ العدّادات تُحدَّث كل 25 مستلماً."""
    from app.database import SessionLocal
    from app.models.bot_poll import BotPoll
    from app.services.telegram_reach import apply_results
    db = SessionLocal()
    try:
        poll = db.query(BotPoll).get(poll_id)
        targets = audience_users(db, poll.audience)
        poll.total = len(targets)
        db.commit()
        results, ok_n, fail_n, last_err = [], 0, 0, None
        for i, (u, tier) in enumerate(targets, 1):
            ok, ptg, err = send_one(token, u.telegram_id, poll.question, poll.options, poll.allows_multiple)
            results.append((u.telegram_id, ok, err))
            if ok:
                ok_n += 1
                _record_message(db, poll.id, ptg, u.telegram_id, u.id, tier)
            else:
                fail_n += 1
                last_err = err
            if i % 25 == 0:
                poll.sent, poll.failed, poll.last_error = ok_n, fail_n, last_err
                db.commit()
            time.sleep(0.05)
        apply_results(db, results)
        poll.sent, poll.failed, poll.last_error = ok_n, fail_n, last_err
        poll.done_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(f"📊 bot poll #{poll_id}: {ok_n}/{len(targets)} أُرسل، فشل {fail_n}")
    except Exception as e:
        logger.error(f"bot poll #{poll_id} send failed: {e}")
    finally:
        db.close()


def record_answer(db, poll_tg_id: str, telegram_id: str, option_ids: list) -> dict:
    """{"survey": False} إن لم يكن تصويتنا (البوت يكمل كتحدّي اليوم). سحب التصويت (option_ids فارغة) يحذف الإجابة."""
    from app.models.bot_poll import BotPollAnswer, BotPollMessage
    msg = db.query(BotPollMessage).filter(BotPollMessage.poll_tg_id == str(poll_tg_id)).first()
    if not msg:
        return {"survey": False}
    row = db.query(BotPollAnswer).filter(BotPollAnswer.poll_id == msg.poll_id,
                                         BotPollAnswer.telegram_id == str(telegram_id)).first()
    first = row is None
    if not option_ids:
        if row:
            db.delete(row)
            db.commit()
        return {"survey": True, "first": False, "retracted": True}
    if row:
        row.option_ids = [int(x) for x in option_ids]
        row.answered_at = datetime.now(timezone.utc)
    else:
        db.add(BotPollAnswer(poll_id=msg.poll_id, telegram_id=str(telegram_id), user_id=msg.user_id, tier=msg.tier,
                             option_ids=[int(x) for x in option_ids]))
    db.commit()
    return {"survey": True, "first": first, "thanks": THANKS if first and msg.tier != "test" else None}


def tally(options: list, answers) -> dict:
    """answers: [(tier, option_ids)] بلا test. النسبة من المصوّتين (الاختيار المتعدد قد يتجاوز 100% بالمجموع)."""
    def count(rows):
        c = [0] * len(options)
        for _, ids in rows:
            for i in ids:
                if 0 <= i < len(c):
                    c[i] += 1
        n = len(rows)
        return {"voters": n, "counts": c, "pct": [round(100 * x / n) if n else 0 for x in c]}
    rows = [(t, ids) for t, ids in answers if t != "test"]
    return {"all": count(rows), "paid": count([r for r in rows if r[0] == "paid"]),
            "trial": count([r for r in rows if r[0] == "trial"])}


def results(db, poll) -> dict:
    from app.models.bot_poll import BotPollAnswer, BotPollMessage
    from app.models.user import User
    ans = db.query(BotPollAnswer).filter(BotPollAnswer.poll_id == poll.id).all()
    msgs = db.query(BotPollMessage.tier).filter(BotPollMessage.poll_id == poll.id, BotPollMessage.tier != "test").all()
    sent_by = {"paid": 0, "trial": 0}
    for (t,) in msgs:
        if t in sent_by:
            sent_by[t] += 1
    uids = [a.user_id for a in ans if a.user_id]
    names = {u.id: u for u in db.query(User).filter(User.id.in_(uids)).all()} if uids else {}
    voters = []
    for a in sorted(ans, key=lambda a: a.answered_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True):
        if a.tier == "test":
            continue
        u = names.get(a.user_id)
        voters.append({"user_id": a.user_id, "name": getattr(u, "full_name", None), "email": getattr(u, "email", None),
                       "telegram_username": getattr(u, "telegram_username", None), "tier": a.tier,
                       "choices": [poll.options[i] for i in a.option_ids if 0 <= i < len(poll.options)],
                       "at": a.answered_at.isoformat() if a.answered_at else None})
    return {"tally": tally(poll.options, [(a.tier, a.option_ids) for a in ans]), "sent_by_tier": sent_by, "voters": voters}


def poll_dict(p) -> dict:
    return {"id": p.id, "question": p.question, "options": p.options, "allows_multiple": p.allows_multiple,
            "audience": p.audience, "created_at": p.created_at.isoformat() if p.created_at else None,
            "sent_at": p.sent_at.isoformat() if p.sent_at else None, "done_at": p.done_at.isoformat() if p.done_at else None,
            "total": p.total, "sent": p.sent, "failed": p.failed, "last_error": p.last_error}
