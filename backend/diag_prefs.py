"""
diag_prefs.py — تشخيص قراءة فقط: ماذا اختار المشتركون فعلاً بالتخصيص؟ (2026-10-12)
==================================================================================
فلتر الفريمات (notify_timeframes) وحد الثقة (notify_min_confidence) محفوظان لكنهما
لا يُطبَّقان على البث إطلاقاً. قبل تطبيقهما نقيس:
  1) توزيع القيم المحفوظة — اللوحة تحفظ ['1h'] و65% افتراضياً حتى لو لم يلمسها
     المشترك، فقيمة محفوظة لا تعني اختياراً واعياً بالضرورة
  2) كم من إشارات آخر 7 أيام كانت ستتوقف لكل مشترك لو طُبّقا

التشغيل:
  docker cp backend/diag_prefs.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/diag_prefs.py 2>/dev/null
"""
import sys
sys.path.insert(0, "/app")
from collections import Counter
from datetime import datetime, timedelta, timezone

from app.database import SessionLocal
from app.models.user import User, PlanType
from app.models.signal import Signal
from app.services.decision_grouping import group_unique_decisions

db = SessionLocal()
users = db.query(User).filter(User.telegram_id != None, User.is_active == True,  # noqa: E711,E712
                              User.plan != PlanType.BANNED).all()
print(f"📊 مشتركون نشطون مرتبطون بتيليجرام: {len(users)}\n")

print("الإشعارات:", Counter("مفعّلة" if u.notifications_enabled is not False else "مُطفأة" for u in users))
print("الأزواج:", Counter("كل الرموز (فارغة)" if not u.notify_watchlist else
                         f"{len(u.notify_watchlist)} رمز" if len(u.notify_watchlist) < 10 else "10+ رموز"
                         for u in users).most_common(8))
print("الفريمات المحفوظة:", Counter(",".join(sorted(u.notify_timeframes)) if u.notify_timeframes else "لا شيء (فارغ)"
                                     for u in users).most_common(10))
print("حد الثقة المحفوظ:", Counter(u.notify_min_confidence for u in users).most_common(10))
upd = Counter("عدّل التفضيلات مرة على الأقل" if u.notify_timeframes else "لم يحفظ التفضيلات أبداً" for u in users)
print("حفظ التفضيلات:", upd, "\n")

since = datetime.now(timezone.utc) - timedelta(days=7)
sigs = db.query(Signal).filter(Signal.created_at >= since, Signal.broadcast_sent == True).all()  # noqa: E712
dec = group_unique_decisions(sigs)
by_id = {s.id: s for s in sigs}
tf_c = Counter(by_id[d["id"]].timeframe for d in dec)
conf = [float(by_id[d["id"]].ai_confidence or 0) for d in dec]
print(f"قرارات مبثوثة آخر 7 أيام: {len(dec)} — حسب الفريم: {dict(tf_c)}")
for th in (50, 60, 65, 70, 75):
    print(f"   ثقتها أقل من {th}%: {sum(1 for c in conf if c < th)} ({sum(1 for c in conf if c < th) * 100 // max(1, len(conf))}%)")

print("\nأثر تطبيق الفلترين لو طُبّقا حرفياً (متوسط الإشارات الأسبوعية التي كانت ستتوقف لكل مشترك):")
lost = []
for u in users:
    tfs = [t for t in (u.notify_timeframes or []) if t != "all"]
    mc = u.notify_min_confidence or 0
    n = sum(1 for d in dec
            if (tfs and by_id[d["id"]].timeframe not in tfs) or float(by_id[d["id"]].ai_confidence or 0) < mc)
    lost.append(n)
if lost:
    lost.sort()
    print(f"   الوسيط: {lost[len(lost) // 2]} من {len(dec)} · الأعلى: {lost[-1]} · من سيخسر أكثر من النصف: "
          f"{sum(1 for x in lost if x > len(dec) / 2)} مشترك")
db.close()
