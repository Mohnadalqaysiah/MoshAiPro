"""
paypal_reconcile_order.py
===========================
يُصلح تحديداً أثر البلاغ "هذا الطلب لا يخصّك" (19/09): بسبب عطل بقراءة
custom_id (راجع DECISIONS.md)، بعض عمليات PayPal كانت **تُحصَّل فعلياً
عند PayPal** بينما نرفضها نحن بـ403 قبل تسجيلها أو تفعيل الاشتراك —
أي مال أُخذ من العميل بلا اشتراك يقابله.

هذه الأداة تأخذ order_id واحداً، تسأل PayPal مباشرة عن حالته الحقيقية،
وتُفعّل الاشتراك **فقط** لو كان محصَّلاً بالفعل (COMPLETED) ولم يُسجَّل
من قبل — idempotent تماماً على tx_id، فتشغيلها أكثر من مرة على نفس
الطلب آمن. لا تلمس أي طلب غير الذي تُمرَّر له صراحة.

من وين تجيب order_id: من سجلات الحاوية وقت الرفض —
  docker logs moshapi_backend --since 24h | grep "ownership mismatch"
السطر يحمل "order=..." — هذا هو المطلوب.

التشغيل:
  docker cp paypal_reconcile_order.py moshapi_backend:/app/
  docker exec moshapi_backend python /app/paypal_reconcile_order.py <ORDER_ID>
"""
import sys
sys.path.insert(0, "/app")


def main():
    if len(sys.argv) != 2:
        print("الاستخدام: python paypal_reconcile_order.py <ORDER_ID>")
        sys.exit(1)
    order_id = sys.argv[1].strip()

    from app.database import SessionLocal
    from app.models.payment import Payment
    from app.api.subscription import (
        _paypal_config, _paypal_access_token, _parse_paypal_custom_id,
        _finalize_paypal_payment, PLANS,
    )
    import requests
    from fastapi import BackgroundTasks

    db = SessionLocal()
    try:
        cfg = _paypal_config(db)
        if not cfg["client_id"] or not cfg["secret_key"]:
            print("❌ مفاتيح PayPal غير مضبوطة بالداشبورد — لا يمكن الاستعلام.")
            return

        token = _paypal_access_token(cfg)
        resp = requests.get(
            f"{cfg['base_url']}/v2/checkout/orders/{order_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        if resp.status_code != 200:
            print(f"❌ تعذّر جلب الطلب من PayPal: {resp.status_code} {resp.text}")
            return

        order = resp.json()
        status = order.get("status")
        print(f"حالة الطلب بحسب PayPal: {status}")

        pu = (order.get("purchase_units") or [{}])[0]
        captures = ((pu.get("payments") or {}).get("captures") or [])

        if status != "COMPLETED" or not captures:
            print("ℹ️ الطلب لم يُحصَّل فعلياً (لا مال أُخذ) — لا حاجة لأي إجراء.")
            return

        capture = captures[0]
        capture_id = capture["id"]
        custom_id = capture.get("custom_id") or pu.get("custom_id") or ""
        owner_id, plan_key, cp_code = _parse_paypal_custom_id(custom_id)
        charged = float(((capture.get("amount") or {}).get("value")) or 0)

        print(f"  capture_id = {capture_id}")
        print(f"  custom_id  = {custom_id!r}  →  user_id={owner_id} plan={plan_key} coupon={cp_code}")
        print(f"  المبلغ المحصَّل فعلياً = ${charged:g}")

        if owner_id is None or plan_key not in PLANS:
            print("❌ تعذّر تحديد المستخدم/الباقة من custom_id — يحتاج تفعيلاً يدوياً من لوحة الإدارة.")
            return

        existing = db.query(Payment).filter(Payment.tx_id == capture_id).first()
        if existing:
            print(f"✅ مسجَّلة أصلاً بقاعدة البيانات (payment_id={existing.id}, status={existing.status}) — لا إجراء.")
            return

        confirm = input(f"\nهل تفعّل الاشتراك للمستخدم {owner_id} بباقة {plan_key} الآن؟ [y/N] ").strip().lower()
        if confirm != "y":
            print("أُلغي — لم يُنفَّذ شيء.")
            return

        payment = _finalize_paypal_payment(
            db, BackgroundTasks(), owner_id, plan_key, capture_id, charged,
            coupon_code=cp_code,
        )
        print(f"✅ تم — payment_id={payment.id}، الاشتراك مفعَّل.")
        print("   (إشعار تلجرام للأدمن وإيميل العميل background tasks — لا")
        print("    تُنفَّذ آلياً بسكربت مستقل عن FastAPI، لا أثر على التفعيل.)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
