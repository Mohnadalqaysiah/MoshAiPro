"""
(2026-11-03) لماذا لم تصل إشارة لمشترك؟ للقراءة فقط، لا يغيّر شيئاً.

يعيد فلاتر البث نفسها (telegram-bot broadcast_new_signals + /active-subscribers) لكل مشترك، ويقرأ سجل التسليم signal_deliveries.
بلا أسماء: كل من سوق الإشارة ضمن تخصيصه (أو بلا تخصيص) ولم يستلمها. مع أسماء: هؤلاء فقط (اسم تيليجرام أو بريد أو رقم حساب).

    docker exec -i moshapi_backend python - 8825 < backend/diag_delivery.py
    docker exec -i moshapi_backend python - 8825 mohmadomer7 someone@mail.com < backend/diag_delivery.py
"""
import sys
from datetime import datetime, timedelta, timezone

_TF_ALIAS = {"1day": "1d"}


def reasons(u, sig, delivered: dict, owners: set, blocked_recent: bool) -> list:
    """أسباب عدم الاستلام بترتيب فلاتر البث. delivered: user_id → (ok, variant, error)."""
    out = []
    if not u.telegram_id:
        out.append("غير مربوط بتيليجرام")
    if not u.is_active or getattr(u.plan, "value", u.plan) == "BANNED":
        out.append("الحساب موقوف")
    if blocked_recent:
        out.append("حظر البوت أو حذف محادثته (رد تيليجرام)")
    if u.notifications_enabled is False:
        out.append("أطفأ إشعارات تيليجرام من التفضيلات")
    wl = {s.upper() for s in (u.notify_watchlist or [])}
    if wl and sig.market.upper() not in wl:
        out.append(f"{sig.market} ليس ضمن أسواقه المختارة: {', '.join(sorted(wl))}")
    tfs = {_TF_ALIAS.get(t, t) for t in (u.notify_timeframes or []) if t != "all"}
    if tfs and sig.timeframe not in tfs:
        out.append(f"اختار فريمات {', '.join(sorted(tfs))} والإشارة {sig.timeframe}")
    if (u.notify_min_confidence or 0) > float(sig.ai_confidence or 0):
        out.append(f"حد الثقة عنده {u.notify_min_confidence}% والإشارة {float(sig.ai_confidence or 0):.0f}%")
    if u.id in owners:
        out.append("وصله تنبيه مراقبة شخصية لنفس الصفقة، فاستُثني من البث حتى لا تصله مرتين")
    d = delivered.get(u.id)
    if d is not None:
        ok, variant, error = d
        out.append(f"✅ وصلته ({'كاملة' if variant == 'full' else 'مموّهة'})" if ok else f"❌ فشل الإرسال: {error}")
    elif not out:
        out.append("لا سبب من الفلاتر ولا سجل تسليم: لم يكن ضمن قائمة المشتركين لحظة البث، أو تخطّى البث الإشارة كلها")
    return out


def main():
    from sqlalchemy import or_
    from app.database import SessionLocal
    from app.models.signal import Signal
    from app.models.signal_delivery import SignalDelivery
    from app.models.user import User
    from app.services.telegram_reach import RETRY_DAYS

    sid, names = int(sys.argv[1]), sys.argv[2:]
    db = SessionLocal()
    sig = db.query(Signal).filter(Signal.id == sid).first()
    if not sig:
        print(f"الإشارة #{sid} غير موجودة")
        return
    rows = db.query(SignalDelivery).filter(SignalDelivery.signal_id == sid).all()
    delivered = {r.user_id: (r.ok, r.variant, r.error) for r in rows if r.user_id}
    ok_n = sum(1 for r in rows if r.ok)
    print(f"#{sid} {sig.market} {sig.timeframe} {getattr(sig.signal_type, 'value', sig.signal_type)} ثقة {float(sig.ai_confidence or 0):.0f}% "
          f"| {sig.created_at:%Y-%m-%d %H:%M} UTC | بُثّت: {bool(sig.broadcast_sent)} | وصلت {ok_n} وفشلت {len(rows) - ok_n}")
    if not rows:
        print("⚠️ لا سجل تسليم إطلاقاً: البث تخطّى هذه الإشارة كلها (قفل الاتجاه، أو صفقة مكافئة بُثّت قبلها، أو عمرها، أو السوق مغلق).")

    # أصحاب صفوف المراقبة الشخصية لنفس الصفقة: نفس السوق والاتجاه وسعر دخول ضمن 0.05%، بين ساعتين قبل الإشارة وبعدها
    near = db.query(Signal.user_id, Signal.entry_price).filter(
        Signal.market == sig.market, Signal.signal_type == sig.signal_type, Signal.user_id.isnot(None),
        Signal.created_at >= sig.created_at - timedelta(hours=2), Signal.created_at <= sig.created_at + timedelta(hours=2)).all()
    owners = {uid for uid, e in near if e and abs(e - sig.entry_price) / sig.entry_price <= 0.0005}

    q = db.query(User)
    if names:
        q = q.filter(or_(User.telegram_username.in_([n.lstrip("@") for n in names]), User.email.in_(names),
                         User.id.in_([int(n) for n in names if n.isdigit()])))
    users = q.all()
    if names:
        missing = [n for n in names if not any(n.lstrip("@") in (u.telegram_username, u.email) or n == str(u.id) for u in users)]
        for n in missing:
            print(f"{n}: لا مستخدم بهذا الاسم أو البريد")
    now = datetime.now(timezone.utc)
    shown = 0
    for u in sorted(users, key=lambda x: x.id):
        wl = {s.upper() for s in (u.notify_watchlist or [])}
        if not names and (not u.telegram_id or (wl and sig.market.upper() not in wl) or delivered.get(u.id, (False,))[0]):
            continue                                                        # الوضع العام: من يخصّه السوق ولم يستلم فقط
        b = u.telegram_blocked_at
        blocked = bool(b and (b if b.tzinfo else b.replace(tzinfo=timezone.utc)) >= now - timedelta(days=RETRY_DAYS))
        print(f"\n#{u.id} @{u.telegram_username or '—'} {u.email} | {getattr(u.plan, 'value', u.plan)}")
        for r in reasons(u, sig, delivered, owners, blocked):
            print(f"   • {r}")
        shown += 1
    if not names:
        print(f"\n{shown} مشتركاً يخصّهم {sig.market} ولم يستلموها.")
    db.close()


if __name__ == "__main__":
    main()
