"""
diag_link_funnel.py — (2026-11-09) أين يتوقف المستخدم قبل ربط تيليجرام؟ قراءة فقط.

سؤال المالك: "نسبة كبيرة لا تربط تيليجرام". قبل أي حل نعرف:
  1. نسبة الربط لكل أسبوع تسجيل — مع تثبيت العمر (≥ MIN_AGE أيام) حتى لا يظهر انحدار وهمي
     (من سجّل أمس لم يمضِ عليه وقت ليربط — نفس تحذير analyze_telegram_link_cohorts.py).
  2. متى يربط من يربط: نفس اليوم أم لاحقاً؟ (إن كان أغلبه نفس اليوم ← لحظة التسجيل هي الفرصة الوحيدة)
  3. من لم يربط: هل استخدم المنصة أصلاً؟ هل فعّل بريده؟ هل سجّل بـGoogle؟ هل عاد خلال آخر 7 أيام؟
     (غير المرتبط النشط = من يمكن إقناعه؛ غير المرتبط الذي لم يستخدم شيئاً = مشكلة تسجيل لا ربط)

  docker exec -i moshapi_backend python - < backend/diag_link_funnel.py
"""
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "/app")

from app.database import SessionLocal  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402

MIN_AGE = 3      # أيام تعرّض أدنى لكل فوج
WEEKS = 8


def _aw(t):
    if t is None:
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def _pct(a, b):
    return f"{(a / b * 100):5.1f}%" if b else "   — "


def funnel(users, now):
    """يرجع جدول الأسابيع وتوزيع وقت الربط وملف غير المرتبطين."""
    weeks = defaultdict(list)
    cutoff = now - timedelta(days=MIN_AGE)
    for u in users:
        c = _aw(u.created_at)
        if c is None or c > cutoff or c < now - timedelta(weeks=WEEKS):
            continue
        wk = (c - timedelta(days=c.weekday())).date()
        weeks[wk].append(u)

    rows = []
    for wk in sorted(weeks):
        us = weeks[wk]
        linked = [u for u in us if u.telegram_id]
        same_day = [u for u in linked if _aw(u.telegram_linked_at) and
                    (_aw(u.telegram_linked_at) - _aw(u.created_at)) <= timedelta(days=1)]
        g = [u for u in us if (u.auth_provider or "") == "google"]
        p = [u for u in us if (u.auth_provider or "") != "google"]
        rows.append((wk, len(us), len(linked), len(same_day),
                     (len(g), sum(1 for u in g if u.telegram_id)), (len(p), sum(1 for u in p if u.telegram_id))))

    lags = defaultdict(int)
    for u in users:
        t, c = _aw(u.telegram_linked_at), _aw(u.created_at)
        if u.telegram_id and t and c and c >= now - timedelta(weeks=WEEKS):
            d = (t - c).total_seconds() / 3600
            lags["≤ ساعة" if d <= 1 else "≤ يوم" if d <= 24 else "≤ 7 أيام" if d <= 168 else "> 7 أيام"] += 1

    pool = [u for us in weeks.values() for u in us]
    un = [u for u in pool if not u.telegram_id]
    li = [u for u in pool if u.telegram_id]
    seen7 = now - timedelta(days=7)

    def prof(group):
        n = len(group)
        return {
            "n": n,
            "used": sum(1 for u in group if (u.analyses_total or 0) + (u.chat_total or 0) > 0),
            "verified": sum(1 for u in group if u.is_verified),
            "google": sum(1 for u in group if (u.auth_provider or "") == "google"),
            "seen7": sum(1 for u in group if _aw(u.last_seen_at) and _aw(u.last_seen_at) >= seen7),
            "pwa": sum(1 for u in group if u.pwa_installed_at),
            "paid": sum(1 for u in group if str(getattr(u.plan, "value", u.plan)) in ("weekly", "monthly", "yearly")),
        }

    return rows, dict(lags), prof(un), prof(li)


def bot_starts(db, now, days=(7, 30)):
    """(2026-11-09) من ضغط Start بلا رابط وهو بلا حساب مربوط: كم هم، وكم ربط منهم لاحقاً."""
    try:
        from app.models.bot_start import BotStart
        rows = db.query(BotStart).all()
    except Exception:
        db.rollback()
        return None
    linked_ids = {t for (t,) in db.query(User.telegram_id).filter(User.telegram_id.isnot(None)).all()}
    admin_ids = {t for (t,) in db.query(User.telegram_id).filter(User.role == UserRole.ADMIN,
                                                               User.telegram_id.isnot(None)).all()}
    rows = [r for r in rows if r.telegram_id not in admin_ids]        # تجارب المالك (فك الربط ثم Start) لا تُحسب
    out = {}
    for d in days:
        since = now - timedelta(days=d)
        new = [r for r in rows if not r.had_account and _aw(r.first_at) and _aw(r.first_at) >= since]
        out[d] = (len(new), sum(1 for r in new if r.telegram_id in linked_ids))
    return out


def main():
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    try:
        users = db.query(User).filter(User.role != UserRole.ADMIN).all()
        rows, lags, un, li = funnel(users, now)
        starts = bot_starts(db, now)
        rem = [u for u in users if getattr(u, "telegram_link_reminded_at", None)]
        rem_linked = sum(1 for u in rem if u.telegram_id and _aw(u.telegram_linked_at)
                         and _aw(u.telegram_linked_at) > _aw(u.telegram_link_reminded_at))
    finally:
        db.close()

    print(f"قمع ربط تيليجرام — آخر {WEEKS} أسابيع، كل فوج عمره ≥ {MIN_AGE} أيام\n")
    print("أسبوع التسجيل   سجّلوا  ربطوا   النسبة   بنفس اليوم        Google          كلمة سر")
    for wk, n, l, sd, (gn, gl), (pn, pl) in rows:
        print(f"{wk}     {n:5}   {l:5}   {_pct(l, n)}   {sd:4} ({_pct(sd, l).strip()})"
              f"   {gl:3}/{gn:<3} {_pct(gl, gn)}   {pl:3}/{pn:<3} {_pct(pl, pn)}")
    tn = sum(r[1] for r in rows)
    tl = sum(r[2] for r in rows)
    print(f"{'المجموع':<14} {tn:5}   {tl:5}   {_pct(tl, tn)}\n")

    tot = sum(lags.values())
    print("متى يربط من يربط (من وقت التسجيل):")
    for k in ("≤ ساعة", "≤ يوم", "≤ 7 أيام", "> 7 أيام"):
        print(f"  {k:<9} {lags.get(k, 0):4}  {_pct(lags.get(k, 0), tot)}")

    print("\nمقارنة: غير المرتبطين مقابل المرتبطين")
    labels = [("used", "استخدم المنصة (تحليل أو شات)"), ("verified", "فعّل بريده"),
              ("google", "سجّل بـGoogle"), ("seen7", "عاد خلال آخر 7 أيام"),
              ("pwa", "ثبّت التطبيق (PWA)"), ("paid", "مشترك مدفوع الآن")]
    print(f"  {'':<30} {'غير مرتبط':>12} {'مرتبط':>12}")
    print(f"  {'العدد':<30} {un['n']:>12} {li['n']:>12}")
    for k, lab in labels:
        print(f"  {lab:<30} {un[k]:>5} {_pct(un[k], un['n'])} {li[k]:>5} {_pct(li[k], li['n'])}")

    print("\nمن ضغط Start بالبوت بلا حساب مربوط (يُسجَّل منذ 2026-11-09):")
    if starts is None:
        print("  الجدول غير موجود بعد (انشر الباك إند أولاً).")
    else:
        for d, (n, l) in starts.items():
            print(f"  آخر {d:>2} يوماً: {n:4} شخصاً، ربط منهم لاحقاً {l:4} ({_pct(l, n).strip()})")
    print(f"\nتذكير الربط بعد يوم من التسجيل: شمل {len(rem)}، ربط منهم بعده {rem_linked} "
          f"({_pct(rem_linked, len(rem)).strip()})")

    print("\nقراءة:")
    print(f"  • غير مرتبط وعاد خلال 7 أيام = {un['seen7']} — هؤلاء من يمكن إقناعهم الآن (تذكير/QR داخل المنصة).")
    print(f"  • غير مرتبط ولم يستخدم شيئاً = {un['n'] - un['used']} — مشكلتهم التسجيل نفسه لا الربط.")


if __name__ == "__main__":
    main()
