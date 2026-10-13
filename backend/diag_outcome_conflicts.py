"""
(2026-10-14) تشخيص للقراءة فقط: صفقة نتيجتها بتيليجرام تختلف عمّا تعرضه المنصة.

بلاغ: إشارة وصلت رابحة على تيليجرام وتظهر خاسرة بالداشبورد. حلقة الرصد ترسل النتيجة **لكل صف**
(صف مُبث → كل المشتركين، صف شخصي → صاحبه فقط)، بينما المنصة تعرض **قراراً واحداً**:
  - صفوف نفس القرار بنتائج مختلفة ← المنصة تعرض نتيجة الأغلبية (status_conflict)
  - صفقة أُعيد إصدارها وهي مفتوحة ونتيجتها خالفت الأولى ← المنصة تعرض نتيجة الأولى (merge_conflict، 13/10)
    (منذ 14/10 لا يُدمج إلا مع تطابق الوقف والهدف أيضاً — حالة AMD لم تعد تُدمج)

يطبع كل حالة: كل نسخة، نتيجتها، من استلم نتيجتها على تيليجرام، وما تعرضه المنصة. لا يكتب شيئاً.

    docker exec moshapi_backend python diag_outcome_conflicts.py [أيام=3]
"""
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from app.database import SessionLocal
from app.models.signal import Signal, SignalStatus
from app.models.signal_delivery import SignalDelivery
from app.models.user import User
from app.services.decision_grouping import group_unique_decisions, merge_reissued

DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 3
AR = {"TP1_HIT": "هدف 1 ✅", "TP2_HIT": "هدف 2 🏆", "SL_HIT": "وقف ❌", "EXPIRED": "منتهية", "ACTIVE": "مفتوحة"}


def _utc(d):
    return d if d is None or d.tzinfo else d.replace(tzinfo=timezone.utc)


def main():
    db = SessionLocal()
    since = datetime.now(timezone.utc) - timedelta(days=DAYS)
    rows = db.query(Signal).filter(Signal.created_at >= since - timedelta(days=3)).all()
    by_id = {s.id: s for s in rows}
    emails = {u.id: (u.email or "", u.telegram_id) for u in db.query(User).filter(User.id.in_({s.user_id for s in rows if s.user_id})).all()}
    deliv = dict(db.query(SignalDelivery.signal_id, func.count(SignalDelivery.id))
                   .filter(SignalDelivery.signal_id.in_(list(by_id)), SignalDelivery.ok == True)  # noqa: E712
                   .group_by(SignalDelivery.signal_id).all()) if by_id else {}

    groups = group_unique_decisions(rows)
    merged = merge_reissued(groups)
    cases = []
    for h in merged:
        ids = h.get("row_ids", []) + h.get("merged_row_ids", [])
        sts = {by_id[i].status.value for i in ids if i in by_id}
        closed_any = any(_utc(by_id[i].exit_executed) and _utc(by_id[i].exit_executed) >= since for i in ids if i in by_id)
        if closed_any and len(sts - {"ACTIVE", "PENDING"}) > 1:
            cases.append((h, ids))

    print(f"آخر {DAYS} يوم: {len(merged)} قرار — منها {len(cases)} بنتائج مختلفة بين نسخها\n")
    for h, ids in sorted(cases, key=lambda c: _utc(c[0]["created_at"]), reverse=True):
        kind = "إعادة إصدار (تُعرض نتيجة الأولى)" if h.get("merged_count") else "نسخ نفس القرار (تُعرض الأغلبية)"
        print(f"■ {h['market']} {h['signal_type']} {h['timeframe']} — صدرت {_utc(h['created_at']):%m-%d %H:%M} UTC — {kind}")
        print(f"   المنصة تعرض: {AR.get(h['status'], h['status'])}")
        for i in sorted(ids, key=lambda i: _utc(by_id[i].created_at)):
            s = by_id[i]
            em, tg = emails.get(s.user_id, ("?", None))
            who = (f"كل المشتركين (بُثّت لـ{deliv.get(i, 0)})" if s.broadcast_sent
                   else f"صاحبها فقط {em.split('@')[0]}{' (تيليجرام)' if tg else ' (بلا تيليجرام)'}")
            src = ("بلا نتيجة بعد" if s.status.value in ("ACTIVE", "PENDING", "EXPIRED")
                   else "رصد تلقائي" if s.current_price is not None
                   else "تصحيح يدوي مؤكد" if s.outcome_verified else "يدوي غير مؤكد")
            ex = _utc(s.exit_executed)
            print(f"   #{s.id:<6} {str(s.timeframe):<4} دخول {s.entry_price} → {AR.get(s.status.value, s.status.value):<10} "
                  f"{(ex.strftime('%m-%d %H:%M') if ex else '—'):<12} {src:<16} نتيجتها أُرسلت لـ: {who}")
        print()
    if not cases:
        print("لا حالات. إن كان البلاغ عن صفقة محددة أرسل الرمز والوقت لفحصها مباشرة.")
    db.close()


if __name__ == "__main__":
    main()
