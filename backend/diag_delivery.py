"""
(2026-11-03) لماذا لم تصل إشارة لمشترك؟ للقراءة فقط، لا يغيّر شيئاً.

يعيد فلاتر البث نفسها (telegram-bot broadcast_new_signals + /active-subscribers) لكل مشترك، ويقرأ سجل التسليم signal_deliveries.
الصفقة الواحدة صف Signal لكل مشترك يراقب الرمز، ويُبث صف واحد منها بالمشتركين: سجل التسليم يُجمع من كل صفوف الصفقة
(نفس الرمز والاتجاه، دخول ضمن 0.05%، خلال ساعتين). النسخة الأولى قرأت الرقم المعطى وحده فبدت الإشارة كأنها لم تصل لأحد.

بلا أسماء: كل من سوق الإشارة ضمن تخصيصه (أو بلا تخصيص) ولم يستلمها. paid: المشتركون المدفوعون وحدهم.
مع أسماء: هؤلاء فقط (اسم تيليجرام أو بريد أو رقم حساب).

    docker exec -i moshapi_backend python - 8825 < backend/diag_delivery.py
    docker exec -i moshapi_backend python - 8825 paid < backend/diag_delivery.py
    docker exec -i moshapi_backend python - 8825 mohmadomer7 someone@mail.com < backend/diag_delivery.py
"""
import sys
from datetime import datetime, timedelta, timezone

_TF_ALIAS = {"1day": "1d"}
SAME_TRADE_TOL = 0.0005


def reasons(u, sig, delivered: dict, owners: set, blocked_recent: bool) -> list:
    """أسباب عدم الاستلام بترتيب فلاتر البث. delivered: user_id → (ok, variant, error). من وصلته يُعرض وصوله وحده."""
    d = delivered.get(u.id)
    if d is not None:
        ok, variant, error = d
        if ok:
            return [f"✅ وصلته ({'كاملة' if variant == 'full' else 'مموّهة'})"]
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
    if d is not None:
        out.append(f"❌ فشل الإرسال: {d[2]}")
    if u.id in owners:
        out.append("وصله تنبيه مراقبة شخصية لنفس الصفقة، فاستُثني من البث حتى لا تصله مرتين")
    if not out:
        out.append("لا سبب من الفلاتر ولا سجل تسليم: لم يكن ضمن قائمة المشتركين لحظة البث")
    return out


def merge_deliveries(rows) -> dict:
    """user_id → (ok, variant, error) من كل صفوف الصفقة؛ وصول ناجح من أي صف يغلب الفشل."""
    out = {}
    for r in rows:
        if not r.user_id:
            continue
        cur = out.get(r.user_id)
        if cur is None or (r.ok and not cur[0]):
            out[r.user_id] = (r.ok, r.variant, r.error)
    return out


def main():
    from sqlalchemy import or_
    from app.database import SessionLocal
    from app.models.signal import Signal
    from app.models.signal_delivery import SignalDelivery
    from app.models.user import User
    from app.services.signal_quota import has_full_access
    from app.services.telegram_reach import RETRY_DAYS

    sid, names = int(sys.argv[1]), sys.argv[2:]
    paid_only = names == ["paid"]
    db = SessionLocal()
    sig = db.query(Signal).filter(Signal.id == sid).first()
    if not sig:
        print(f"الإشارة #{sid} غير موجودة")
        return
    near = db.query(Signal).filter(
        Signal.market == sig.market, Signal.signal_type == sig.signal_type,
        Signal.created_at >= sig.created_at - timedelta(hours=2), Signal.created_at <= sig.created_at + timedelta(hours=2)).all()
    siblings = [s for s in near if s.entry_price and abs(s.entry_price - sig.entry_price) / sig.entry_price <= SAME_TRADE_TOL]
    ids = [s.id for s in siblings]
    owners = {s.user_id for s in siblings if s.user_id}
    rows = db.query(SignalDelivery).filter(SignalDelivery.signal_id.in_(ids)).all()
    delivered = merge_deliveries(rows)
    by_sig = {}
    for r in rows:
        by_sig.setdefault(r.signal_id, [0, 0])[0 if r.ok else 1] += 1
    print(f"#{sid} {sig.market} {sig.timeframe} {getattr(sig.signal_type, 'value', sig.signal_type)} ثقة {float(sig.ai_confidence or 0):.0f}% "
          f"| {sig.created_at:%Y-%m-%d %H:%M} UTC")
    print(f"   نفس الصفقة محفوظة في {len(ids)} صفاً (صف لكل مشترك يراقبها). البث العام: "
          + ("، ".join(f"#{k} وصلت {v[0]} وفشلت {v[1]}" for k, v in sorted(by_sig.items())) if by_sig else "لا شيء"))
    if not rows:
        print("⚠️ لا سجل تسليم لأي صف من الصفقة: البث العام تخطّاها (قفل الاتجاه، أو صفقة مكافئة بُثّت قبلها، أو عمرها، أو السوق مغلق).")

    q = db.query(User)
    if names and not paid_only:
        q = q.filter(or_(User.telegram_username.in_([n.lstrip("@") for n in names]), User.email.in_(names),
                         User.id.in_([int(n) for n in names if n.isdigit()])))
    users = q.all()
    if names and not paid_only:
        for n in names:
            if not any(n.lstrip("@") in (u.telegram_username, u.email) or n == str(u.id) for u in users):
                print(f"{n}: لا مستخدم بهذا الاسم أو البريد")
    now = datetime.now(timezone.utc)
    shown, counts = 0, {}
    for u in sorted(users, key=lambda x: x.id):
        wl = {s.upper() for s in (u.notify_watchlist or [])}
        if paid_only and not has_full_access(u):
            continue
        if not names and (not u.telegram_id or (wl and sig.market.upper() not in wl) or delivered.get(u.id, (False,))[0]):
            continue                                                        # الوضع العام: من يخصّه السوق ولم يستلم فقط
        b = u.telegram_blocked_at
        blocked = bool(b and (b if b.tzinfo else b.replace(tzinfo=timezone.utc)) >= now - timedelta(days=RETRY_DAYS))
        rs = reasons(u, sig, delivered, owners, blocked)
        print(f"\n#{u.id} @{u.telegram_username or '—'} {u.email} | {getattr(u.plan, 'value', u.plan)}")
        for r in rs:
            print(f"   • {r}")
        key = rs[0].split(":")[0].split("(")[0].strip()
        counts[key] = counts.get(key, 0) + 1
        shown += 1
    print(f"\nالمجموع {shown}:")
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"   {v:>4}  {k}")
    db.close()


if __name__ == "__main__":
    main()
