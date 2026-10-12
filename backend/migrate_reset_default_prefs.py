"""
migrate_reset_default_prefs.py — تصحيح قيم التخصيص التلقائية (2026-10-12)
==========================================================================
صفحة الإعدادات كانت تحفظ "ساعة" للفريم و65% لحد الثقة تلقائياً لكل من ضغط
"حفظ" حتى لو لم يلمسهما. الفلتران لم يُطبَّقا على البث أبداً فلم يظهر الخلل —
والآن سيُطبَّقان. diag_prefs.py: لو طُبّقا حرفياً لخسر 270 من 280 مشتركاً أكثر
من نصف إشاراتهم (51% من الإشارات ثقتها < 65%).

بقرار صاحب المنتج: القيمتان التلقائيتان تُعامَلان كـ"لم يختر":
  - notify_min_confidence == 65   → 0  (كل الإشارات)
  - notify_timeframes == ['1h']   → [] (كل الفريمات)
أي قيمة أخرى (80%، 15m فقط، ...) اختيار واعٍ وتبقى كما هي وتُطبَّق.

⚠️ DRY-RUN افتراضياً. التطبيق بـ--apply.
التشغيل:
  docker cp backend/migrate_reset_default_prefs.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/migrate_reset_default_prefs.py 2>/dev/null
  docker exec moshapi_backend python /app/migrate_reset_default_prefs.py --apply 2>/dev/null
"""
import sys
sys.path.insert(0, "/app")
from app.database import SessionLocal
from app.models.user import User

APPLY = "--apply" in sys.argv
db = SessionLocal()
users = db.query(User).all()
conf_reset = [u for u in users if u.notify_min_confidence == 65]
tf_reset = [u for u in users if list(u.notify_timeframes or []) == ["1h"]]
kept_conf = [u for u in users if u.notify_min_confidence not in (None, 0, 65)]
kept_tf = [u for u in users if (u.notify_timeframes or []) not in ([], ["1h"], ["all"])]

print(f"حد الثقة 65% → كل الإشارات: {len(conf_reset)} مستخدم")
print(f"فريم 'ساعة' فقط → كل الفريمات: {len(tf_reset)} مستخدم")
print(f"اختيارات واعية تبقى وتُطبَّق: حد ثقة {len(kept_conf)} · فريمات {len(kept_tf)}")
for u in kept_tf[:30]:
    print(f"   #{u.id} فريمات: {u.notify_timeframes}")

if APPLY:
    for u in conf_reset:
        u.notify_min_confidence = 0
    for u in tf_reset:
        u.notify_timeframes = []
    db.commit()
    print("✅ تم التطبيق.")
else:
    print("ℹ️ معاينة فقط — للتطبيق: --apply")
db.close()
