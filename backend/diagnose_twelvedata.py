"""
diagnose_twelvedata.py
=========================
تشخيص قراءة فقط لمصدر السعر اللحظي (TwelveData) — يجاوب بدقة:
هل هو مفعّل؟ هل المفتاح موجود؟ وإذا كان موجوداً، ماذا يرد الـAPI فعلاً؟

⚠️ لا يطبع المفتاح إطلاقاً — فقط وجوده وطوله، ورسالة الـAPI.

التشغيل:
  docker cp diagnose_twelvedata.py moshapi_backend:/app/
  docker compose -f docker-compose.prod.yml exec backend python /app/diagnose_twelvedata.py
"""
import sys
sys.path.insert(0, "/app")

import requests
from app.config import get_settings
from app.database import SessionLocal
from app.models.site_settings import SiteSettings
from app.services.smart_data import smart_data, TWELVEDATA_MAP


def mask(v):
    """يصف المفتاح بدون كشفه."""
    if not v:
        return "غير موجود"
    return f"موجود (طول={len(v)}، ينتهي بـ…{v[-3:]})"


def main():
    settings = get_settings()

    print("=" * 84)
    print("1) حالة الـruntime داخل العملية الحالية")
    print("=" * 84)
    print(f"  smart_data._td_enabled      = {smart_data._td_enabled}")
    print(f"  smart_data._td_runtime_key  = {mask(smart_data._td_runtime_key)}")
    print(f"  settings.TWELVEDATA_API_KEY = {mask(settings.TWELVEDATA_API_KEY)}")
    print(f"  TWELVEDATA_MAP['XAUUSD']    = {TWELVEDATA_MAP.get('XAUUSD')}")
    print(f"  TWELVEDATA_MAP['XAGUSD']    = {TWELVEDATA_MAP.get('XAGUSD')}")

    print("\n" + "=" * 84)
    print("2) الإعداد المحفوظ بقاعدة البيانات (SiteSettings)")
    print("=" * 84)
    db = SessionLocal()
    try:
        rows = {r.key: (r.value or "") for r in db.query(SiteSettings).filter(
            SiteSettings.key.in_(["twelvedata_api_key", "twelvedata_enabled"])).all()}
    finally:
        db.close()
    if not rows:
        print("  لا يوجد أي صف — الإعداد لم يُضبط من لوحة الإدارة إطلاقاً.")
    print(f"  twelvedata_enabled  = {rows.get('twelvedata_enabled', '(الصف غير موجود)')}")
    print(f"  twelvedata_api_key  = {mask(rows.get('twelvedata_api_key', ''))}")

    print("\n" + "=" * 84)
    print("3) هل main.py الجديد (استعادة الإعداد بالإقلاع) موجود داخل الحاوية؟")
    print("=" * 84)
    try:
        with open("/app/app/main.py", encoding="utf-8") as f:
            src = f.read()
        print("  'TwelveData restored' موجود بالملف: "
              + ("نعم ✅" if "TwelveData restored" in src else "لا ❌ (الصورة قديمة — لم يُعد البناء)"))
    except Exception as e:
        print(f"  تعذّر القراءة: {e}")

    print("\n" + "=" * 84)
    print("4) اتصال حقيقي بـTwelveData /price")
    print("=" * 84)
    key = (rows.get("twelvedata_api_key", "").strip()
           or smart_data._td_runtime_key
           or settings.TWELVEDATA_API_KEY)
    if not key:
        print("  ⛔ لا يوجد مفتاح إطلاقاً — لا يمكن الاختبار.")
        return
    for sym in ("XAU/USD", "XAG/USD"):
        try:
            r = requests.get("https://api.twelvedata.com/price",
                             params={"symbol": sym, "apikey": key}, timeout=8)
            data = r.json()
        except Exception as e:
            print(f"  {sym}: ❌ استثناء شبكي: {type(e).__name__}: {e}")
            continue
        if isinstance(data, dict) and "price" in data:
            print(f"  {sym}: ✅ السعر = {data['price']}")
        else:
            # نطبع رسالة الخطأ فقط — لا نطبع الرد الخام تجنّباً لأي تسريب
            code = data.get("code") if isinstance(data, dict) else None
            msg  = data.get("message") if isinstance(data, dict) else None
            status = data.get("status") if isinstance(data, dict) else None
            print(f"  {sym}: ❌ لا يوجد سعر — status={status} code={code}")
            print(f"       message: {msg}")


if __name__ == "__main__":
    main()
