"""
Mosh AI Pro v5 - Web Push Notifications
إشعارات متصفح حقيقية (Web Push API) — تصل حتى بدون فتح التبويب، بشرط
المتصفح شغّال. قناة موازية لتيليجرام، لا بديلة عنها: أساسها خدمة عميل
ما ربط حسابه بتيليجرام (لا يصله أي تنبيه شخصي حالياً بلا هاي القناة).

سبب استخدام pywebpush مباشرة لا مكتبة أعلى مستوى: نفس فلسفة Gemini HTTP
المباشر بالمشروع — تحكّم كامل بلا طبقة وسيطة غير ضرورية.
"""
import json
from loguru import logger
from sqlalchemy.orm import Session

from app.config import get_settings

_s = get_settings()


def push_enabled() -> bool:
    return bool(_s.VAPID_PUBLIC_KEY and _s.VAPID_PRIVATE_KEY)


def send_push(db: Session, user, title: str, body: str, url: str = "/dashboard", tag: str = "signal") -> int:
    """يرسل لكل اشتراكات المستخدم (كل متصفح/جهاز سجّله). يحذف أي اشتراك
    منتهي/مرفوض (410/404) تلقائياً. يعيد عدد الإرسالات الناجحة."""
    if not push_enabled():
        return 0

    from pywebpush import webpush, WebPushException
    from app.models.push_subscription import PushSubscription

    subs = db.query(PushSubscription).filter(PushSubscription.user_id == user.id).all()
    if not subs:
        return 0

    # (2026-09-28) سجل داخل التطبيق — زر "🔔" يعرض آخر إشعارات المستخدم
    # حتى لو فاته/رفض إشعار المتصفح نفسه (شائع بالهاتف). مرة واحدة لكل
    # إشعار بغض النظر عن عدد أجهزته المشترَكة تحت — لا تكرار بكل جهاز.
    from app.models.notification import Notification
    db.add(Notification(user_id=user.id, title=title, body=body, url=url, tag=tag))

    payload = json.dumps({"title": title, "body": body, "url": url, "tag": tag})
    sent = 0
    for sub in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=_s.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": f"mailto:{_s.VAPID_CLAIM_EMAIL}"},
            )
            sent += 1
        except WebPushException as e:
            status = getattr(e.response, "status_code", None)
            if status in (404, 410):
                db.delete(sub)
            else:
                logger.warning(f"Web push failed (user={user.id}): {e}")
        except Exception as e:
            logger.warning(f"Web push error (user={user.id}): {e}")

    if sent or subs:
        db.commit()
    return sent
