"""
diagnose_duplicate_outcomes.py
===============================
قراءة محضة — لا يعدّل صفاً. بلاغ 21/09: رسالة "وقف الخسارة ضُرب" وصلت
5 مرات متطابقة لإشارة NAS100 بيع، ورسالة "الهدف 2 تحقق" وصلت مرتين
لإشارة S&P500 — والسؤال المباشر: هل NAS100 لسا ACTIVE بقاعدة البيانات
رغم رسائل الإغلاق المتكررة؟

يطبع الحالة الفعلية بقاعدة البيانات لكل إشارة NAS100/S&P500 بيع بآخر
48 ساعة، وعدد صفوف Signal لكل قرار (decision) — لو تعدّدت الصفوف لنفس
القرار بأكثر من رمز واحد فهو بث طبيعي (تجميع)، بينما تكرار رسائل لنفس
الصف بالضبط يعني إعادة إرسال، لا إشارات متعددة.

التشغيل:
  docker cp diagnose_duplicate_outcomes.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/diagnose_duplicate_outcomes.py
"""
import sys, asyncio
sys.path.insert(0, "/app")

from datetime import datetime, timezone, timedelta


async def main():
    from app.database import SessionLocal
    from app.models.signal import Signal

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        since = now - timedelta(hours=48)
        rows = (db.query(Signal)
                  .filter(Signal.market.in_(["NAS100", "SP500", "US30"]))
                  .filter(Signal.created_at >= since)
                  .order_by(Signal.created_at.desc()).all())

        print("=" * 100)
        print(f"إشارات NAS100/SP500 آخر 48 ساعة — {now:%Y-%m-%d %H:%M} UTC")
        print("=" * 100)
        if not rows:
            print("لا صفوف — تحقق من اسم الرمز المخزَّن فعلياً بالجدول (market).")

        for s in rows:
            c = s.created_at
            if c and c.tzinfo is None:
                c = c.replace(tzinfo=timezone.utc)
            u = s.updated_at
            if u and u.tzinfo is None:
                u = u.replace(tzinfo=timezone.utc)
            stype = s.signal_type.value if hasattr(s.signal_type, "value") else s.signal_type
            status = s.status.value if hasattr(s.status, "value") else s.status
            print(f"\n#{s.id}  {s.market}  {stype}  user_id={s.user_id}")
            print(f"   أُنشئت: {c:%m-%d %H:%M} UTC   آخر تحديث: {u:%m-%d %H:%M} UTC" if u else f"   أُنشئت: {c:%m-%d %H:%M} UTC   آخر تحديث: —")
            print(f"   status = {status}")
            print(f"   دخول={s.entry_price}  وقف={s.stop_loss}  هدف1={s.take_profit_1}  هدف2={s.take_profit_2}")
            print(f"   expires_at={s.expires_at}")

        print("\n" + "=" * 100)
        print("الخلاصة")
        print("=" * 100)
        for s in rows:
            status = s.status.value if hasattr(s.status, "value") else s.status
            if status in ("PENDING", "ACTIVE"):
                print(f"  ⚠️ #{s.id} ({s.market} user={s.user_id}) لسا status={status} — لم يُغلق رغم رسائل الإغلاق المرسَلة")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
