"""
migrate_cleanup_empty_support_threads.py
=========================================
(2026-09-06) اكتُشف إن GET /api/v1/support/thread كان يُنشئ صف محادثة
support_chat_threads لأي مستخدم مسجّل دخول بمجرد ما الفرونت يفحص عداد
الرسائل غير المقروءة (كل 20 ثانية، بغض النظر إن كان المستخدم فتح الشات
أو أرسل أي رسالة) — سبب ظهور عشرات "المحادثات المفتوحة" بلوحة الإدارة
لمستخدمين لم يرسلوا شيئاً أبداً. تم تصحيح الكود (support.py) ليصير
read-only ولا ينشئ صف إلا عند إرسال رسالة فعلية.

هذا السكربت ينظّف الصفوف الفاضية (0 رسالة) يلي اتخلقت بالغلط سابقاً —
لا يمس أي محادثة فيها ولو رسالة وحدة.

التشغيل:
  docker cp migrate_cleanup_empty_support_threads.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/migrate_cleanup_empty_support_threads.py
"""
import sys
sys.path.insert(0, "/app")

from app.database import SessionLocal
from app.models.support_chat import SupportChatThread, SupportChatMessage


def cleanup():
    db = SessionLocal()
    try:
        threads = db.query(SupportChatThread).all()
        empty = [t for t in threads if db.query(SupportChatMessage).filter(SupportChatMessage.thread_id == t.id).count() == 0]

        print(f"📊 إجمالي المحادثات: {len(threads)}  —  فاضية (0 رسالة): {len(empty)}")
        for t in empty:
            u = t.user
            print(f"  🗑️  thread #{t.id}  user_id={t.user_id}  ({u.email if u else '?'})  created_at={t.created_at}")
            db.delete(t)

        db.commit()
        print(f"✅ تم حذف {len(empty)} محادثة فاضية")
    finally:
        db.close()


if __name__ == "__main__":
    cleanup()
