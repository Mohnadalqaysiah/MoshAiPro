"""
(2026-11-09) لماذا يحظر المستخدمون البوت؟ للقراءة فقط، لا يغيّر شيئاً.

لا يُسجَّل وقت الحظر نفسه: telegram_blocked_at يتجدد مع كل محاولة فاشلة. الوقت المقدَّر = أول إرسال فشل برد "محظور" بسجل التسليم
(signal_deliveries، إشارات البث فقط، منذ 16/09)، والحظر وقع بينه وبين آخر إرسال ناجح قبله. رسائل النتائج والإعلانات والتنبيهات الأخرى
لا تُسجَّل فيه، فعدد "ما وصله" حد أدنى.

لكل من حظر: الأيام من ربط تيليجرام حتى الحظر، وحالته وقتها (تجربة، بعد التجربة، مدفوع)، وكم رسالة وصلته يومياً، ونسبة المموّهة
بآخر 20 رسالة، ونتائج آخر 5 إشارات وصلته، وهل جاء الحظر خلال 48 ساعة من إعلان جماعي. ثم مقارنة بمن لم يحظر.

    docker exec -i moshapi_backend python - < backend/diag_blocked_users.py
"""
from collections import Counter
from datetime import datetime, timedelta, timezone

DAY_BUCKETS = [(1, "أقل من يوم"), (3, "1–3 أيام"), (7, "3–7 أيام"), (14, "7–14 يوماً"), (10 ** 6, "أكثر من 14 يوماً")]


def _aware(d):
    return d if d is None or d.tzinfo else d.replace(tzinfo=timezone.utc)


def bucket(days: float) -> str:
    return next(label for edge, label in DAY_BUCKETS if days < edge)


def block_profile(user, rows, outcome_of, paid_before, broadcasts, unreachable) -> dict:
    """rows: [(sent_at, ok, variant, error, signal_id)] لهذا المستخدم. None = لم يحظر بحسب سجل التسليم."""
    rows = sorted(rows, key=lambda r: _aware(r[0]))
    fails = [r for r in rows if not r[1] and unreachable(r[3])]
    if not fails:
        return None
    t_block = _aware(fails[0][0])
    before = [r for r in rows if r[1] and _aware(r[0]) < t_block]
    start = _aware(user.telegram_linked_at) or _aware(user.created_at) or (_aware(before[0][0]) if before else t_block)
    days = max((t_block - start).total_seconds() / 86400, 0.0)
    trial_end = _aware(user.trial_ends_at)
    if paid_before(user.id, t_block):
        status = "مدفوع"
    elif trial_end and t_block <= trial_end:
        status = "أثناء التجربة"
    else:
        status = "بعد انتهاء التجربة"
    last20 = before[-20:]
    last5 = [outcome_of.get(r[4]) for r in before[-5:]]
    return {
        "days": days, "bucket": bucket(days), "status": status, "received": len(before),
        "per_day": len(before) / max(days, 1.0),
        "masked_share": (sum(1 for r in last20 if r[2] == "masked") / len(last20)) if last20 else None,
        "last5_sl": sum(1 for o in last5 if o == "SL_HIT"), "last5_known": sum(1 for o in last5 if o),
        "after_broadcast": any(timedelta(0) <= t_block - _aware(b) <= timedelta(hours=48) for b in broadcasts),
        "returned": any(r[1] and _aware(r[0]) > t_block for r in rows),
    }


def _pct(n, d):
    return f"{100 * n / d:.0f}%" if d else "—"


def main():
    from app.database import SessionLocal
    from app.models.payment import Payment, PaymentStatus
    from app.models.signal import Signal
    from app.models.signal_delivery import SignalDelivery
    from app.models.telegram_broadcast import TelegramBroadcast
    from app.models.user import User
    from app.services.telegram_reach import is_unreachable

    db = SessionLocal()
    now = datetime.now(timezone.utc)
    users = {u.id: u for u in db.query(User).filter(User.telegram_id.isnot(None)).all()}
    by_user = {}
    for r in db.query(SignalDelivery.user_id, SignalDelivery.sent_at, SignalDelivery.ok, SignalDelivery.variant,
                      SignalDelivery.error, SignalDelivery.signal_id).filter(SignalDelivery.user_id.isnot(None)).yield_per(5000):
        by_user.setdefault(r[0], []).append(r[1:])
    sig_ids = {r[4] for rows in by_user.values() for r in rows}
    outcome_of = {i: getattr(st, "value", st) for i, st in db.query(Signal.id, Signal.status).filter(Signal.id.in_(sig_ids))} if sig_ids else {}
    paid = {}
    for uid, t in db.query(Payment.user_id, Payment.created_at).filter(Payment.status == PaymentStatus.APPROVED):
        paid.setdefault(uid, []).append(_aware(t))
    paid_before = lambda uid, t: any(p <= t for p in paid.get(uid, []))
    broadcasts = [b for (b,) in db.query(TelegramBroadcast.created_at)]

    prof, keep = {}, []
    for uid, rows in by_user.items():
        u = users.get(uid)
        if not u:
            continue
        p = block_profile(u, rows, outcome_of, paid_before, broadcasts, is_unreachable)
        if p:
            prof[uid] = p
        elif any(r[1] for r in rows):
            first = min(_aware(r[0]) for r in rows)
            ok = sum(1 for r in rows if r[1])
            last20 = sorted([r for r in rows if r[1]], key=lambda r: _aware(r[0]))[-20:]
            keep.append({"per_day": ok / max((now - first).total_seconds() / 86400, 1.0),
                         "masked_share": sum(1 for r in last20 if r[2] == "masked") / len(last20) if last20 else None})

    flagged = sum(1 for u in users.values() if u.telegram_blocked_at)
    B = list(prof.values())
    n = len(B)
    print(f"مرتبطون بتيليجرام: {len(users)} | حظروا بحسب سجل التسليم: {n} (منهم {sum(p['returned'] for p in B)} عادوا) | "
          f"معلَّمون محظورين الآن: {flagged} | لم يحظروا ولهم تسليم ناجح: {len(keep)}\n")
    if not n:
        print("لا حظر في سجل التسليم.")
        return

    print("── متى حظروا (من ربط تيليجرام حتى أول إرسال فشل)")
    c = Counter(p["bucket"] for p in B)
    for _, label in DAY_BUCKETS:
        print(f"   {label:<18} {c[label]:>4}  {_pct(c[label], n)}")
    print("\n── حالتهم وقت الحظر")
    for k, v in Counter(p["status"] for p in B).most_common():
        print(f"   {k:<18} {v:>4}  {_pct(v, n)}")

    def avg(xs):
        xs = [x for x in xs if x is not None]
        return sum(xs) / len(xs) if xs else None
    fmt = lambda v, pct=False: "—" if v is None else (f"{100 * v:.0f}%" if pct else f"{v:.1f}")
    print("\n── كثافة الرسائل (إشارات البث فقط)")
    print(f"   من حظروا: {fmt(avg(p['per_day'] for p in B))} إشارة يومياً قبل الحظر، المموّهة بآخر 20: {fmt(avg(p['masked_share'] for p in B), True)}")
    print(f"   من لم يحظروا: {fmt(avg(k['per_day'] for k in keep))} إشارة يومياً، المموّهة بآخر 20: {fmt(avg(k['masked_share'] for k in keep), True)}")
    print(f"   وصلهم قبل الحظر: وسيط {sorted(p['received'] for p in B)[n // 2]} إشارة، ووصل {sum(1 for p in B if p['received'] == 0)} منهم صفر إشارة ناجحة")

    print("\n── ما سبق الحظر مباشرة")
    known = [p for p in B if p["last5_known"] >= 3]
    heavy = sum(1 for p in known if p["last5_sl"] >= 3)
    print(f"   3 خسائر فأكثر بآخر 5 إشارات وصلته: {heavy} من {len(known)} ({_pct(heavy, len(known))})")
    print(f"   خلال 48 ساعة بعد إعلان جماعي: {sum(p['after_broadcast'] for p in B)} من {n} ({_pct(sum(p['after_broadcast'] for p in B), n)})"
          f" — {len(broadcasts)} إعلاناً مسجّلاً")
    print("\nتنبيه: وقت الحظر مقدَّر بأول فشل، والمقارنات وصف لا سبب. أي فرضية هنا تُختبر قبل تغيير الرسائل.")
    db.close()


if __name__ == "__main__":
    main()
