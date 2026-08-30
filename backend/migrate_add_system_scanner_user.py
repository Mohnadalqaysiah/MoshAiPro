"""
migrate_add_system_scanner_user.py
ينشئ حساب نظام مخصص لبث market_scanner.py — حساب داخلي بلا telegram_id
وبلا notify_watchlist إطلاقاً، عشان broadcast_new_signals بالبوت يوزّع
إشاراته على كل المشتركين (نفس منطق "مستخدم بدون watchlist يستلم كل شيء")
بدل ما تنحصر بمراقبة شخص واحد. غير قابل لتسجيل الدخول فعلياً (كلمة سر
عشوائية غير معروفة لأحد) — دوره فقط FK لعمود signals.user_id.

Run: docker exec moshapi_backend python /app/migrate_add_system_scanner_user.py
"""
import sys
sys.path.insert(0, "/app")
import secrets
from app.database import SessionLocal
from app.models.user import User, UserRole, PlanType
from app.services.auth_service import hash_password
from app.models import payment, signal, analysis_log, affiliate, price_alert, strategy  # noqa: F401

SYSTEM_SCANNER_EMAIL = "system-scanner@qaffel.internal"


def migrate():
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == SYSTEM_SCANNER_EMAIL).first()
        if existing:
            print(f"ℹ️  System scanner user already exists (id={existing.id}) — skipping")
            return

        user = User(
            email=SYSTEM_SCANNER_EMAIL,
            password_hash=hash_password(secrets.token_urlsafe(32)),  # لا أحد يعرف القيمة — دخول غير ممكن
            full_name="Qaffel Market Scanner (System)",
            role=UserRole.USER,
            is_active=True,
            is_verified=True,
            plan=PlanType.MONTHLY,   # يتجنب أي فحص متعلق بحدود التجربة لو استُخدم بالخطأ بمسار آخر
            telegram_id=None,        # مقصود — يستبعده تلقائياً من active-subscribers/all-watchlists
            notify_watchlist=[],
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"✅ System scanner user created — id={user.id}, email={SYSTEM_SCANNER_EMAIL}")
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
