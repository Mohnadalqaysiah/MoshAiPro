"""
(2026-10-31، طلب المالك) عدد إشارات القناة العامة المفتوحة يومياً، والباقي مموّه.

العدد من اللوحة: channel_open_daily (0 أو غير موجود = الكل مموّه كما كان). العدّ بقاعدة البيانات لا بذاكرة البوت، حتى لا تفتح
إعادة تشغيله إشارات فوق ما حدده المالك. اليوم بتوقيت UTC، مثل TeaserGate بالبوت. أول N إشارة تُنشر باليوم، بلا أي اختيار.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.site_settings import SiteSettings

LIMIT_KEY = "channel_open_daily"
USED_KEY = "channel_open_used"     # "2026-10-31:2" — يكتبه الخادم، ليس إعداداً للمالك


def _limit(db: Session) -> int:
    row = db.query(SiteSettings).filter(SiteSettings.key == LIMIT_KEY).first()
    try:
        return max(0, int((row.value or "0").strip())) if row else 0
    except ValueError:
        return 0


def claim(db: Session, now: Optional[datetime] = None) -> bool:
    """True = المنشور التالي مفتوح، ويُحسب من عدد اليوم."""
    limit = _limit(db)
    if limit <= 0:
        return False
    day = (now or datetime.now(timezone.utc)).date().isoformat()
    row = db.query(SiteSettings).filter(SiteSettings.key == USED_KEY).with_for_update().first()
    if row is None:
        row = SiteSettings(key=USED_KEY, value=f"{day}:0", description="عدّاد إشارات القناة المفتوحة اليوم (تلقائي)")
        db.add(row)
    used_day, _, used = (row.value or "").partition(":")
    used = int(used) if used_day == day and used.isdigit() else 0
    if used >= limit:
        return False
    row.value = f"{day}:{used + 1}"
    db.commit()
    return True
