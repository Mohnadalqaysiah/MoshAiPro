"""
firebase_auth.py — التحقق من Firebase ID Token (تسجيل الدخول بحساب Google)
==========================================================================
يتحقق أن الـID token الآتي من الفرونت-إند (بعد signInWithPopup بقوقل)
صادر فعلاً من مشروع Firebase الخاص بنا ولم يُزوَّر، ويُرجع بيانات
المستخدم الموثَّقة (بريد، اسم، هل البريد مؤكَّد).

التهيئة كسولة (lazy) — لا تحاول تحميل ملف الاعتماد إلا عند أول استدعاء
فعلي، حتى لا يفشل استيراد التطبيق كاملاً لو FIREBASE_CREDENTIALS_PATH غير
مضبوط بعد على بيئة معيّنة (تطوير محلي مثلاً).
"""
from typing import Optional
from loguru import logger

from app.config import get_settings

_app = None  # firebase_admin.App singleton، يُهيَّأ مرة واحدة فقط


class FirebaseNotConfigured(Exception):
    """FIREBASE_CREDENTIALS_PATH غير مضبوط أو الملف غير موجود/غير صالح."""


def _get_app():
    global _app
    if _app is not None:
        return _app

    settings = get_settings()
    path = settings.FIREBASE_CREDENTIALS_PATH
    if not path:
        raise FirebaseNotConfigured("FIREBASE_CREDENTIALS_PATH غير مضبوط بـ.env.prod")

    import firebase_admin
    from firebase_admin import credentials

    try:
        cred = credentials.Certificate(path)
        _app = firebase_admin.initialize_app(cred)
        logger.success("✅ Firebase Admin مهيَّأ — تسجيل الدخول بقوقل فعّال")
        return _app
    except FileNotFoundError:
        raise FirebaseNotConfigured(f"ملف الاعتماد غير موجود: {path}")
    except Exception as e:
        raise FirebaseNotConfigured(f"فشل تحميل ملف اعتماد Firebase: {e}")


def verify_google_id_token(id_token: str) -> dict:
    """
    يتحقق من الـID token ويُرجع:
      {"email": str, "email_verified": bool, "name": str | None, "uid": str}

    يرمي firebase_admin.auth.InvalidIdTokenError (أو مشتقاتها) لو التوكن
    غير صالح/منتهي/مزوَّر — يُترك للمستدعي ليترجمه لرسالة مناسبة.
    يرمي FirebaseNotConfigured لو الخادم نفسه غير مهيَّأ بعد.
    """
    from firebase_admin import auth as fb_auth

    app = _get_app()
    decoded = fb_auth.verify_id_token(id_token, app=app)

    email: Optional[str] = decoded.get("email")
    if not email:
        # نظرياً لا يحصل لمزوّد Google (يطلب النطاق email دائماً)، لكن حارس صريح أوضح من KeyError لاحقاً
        raise ValueError("Google token بلا بريد إلكتروني")

    return {
        "email": email.lower().strip(),
        "email_verified": bool(decoded.get("email_verified", False)),
        "name": decoded.get("name") or "",
        "uid": decoded.get("uid", ""),
    }
