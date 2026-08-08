"""
migrate_add_gulf_markets.py
يضيف الأسواق الخليجية/السعودية إلى جدول market_configs حتى تظهر باللوحة
الرئيسية والإشارات (مو بس بأداة Strategy Builder). كل الرموز متحقق منها
حياً مقابل TradingView قبل إضافتها هون — راجع smart_data.py::GULF_SYMBOL_MAP
للمصدر الفعلي للبيانات.

Run: docker exec moshapi_backend python /app/migrate_add_gulf_markets.py
"""
import sys
sys.path.insert(0, "/app")
from app.database import SessionLocal
from app.models.market_config import MarketConfig

# (symbol, display_name, sort_order) — نفس الترتيب المنطقي: تداول أولاً ثم باقي الخليج
GULF_MARKETS = [
    ("ARAMCO",      "أرامكو السعودية",              100),
    ("RAJHI",       "مصرف الراجحي",                  101),
    ("SABIC",       "سابك",                          102),
    ("STC",         "الاتصالات السعودية STC",        103),
    ("SNB",         "البنك الأهلي السعودي",          104),
    ("MAADEN",      "معادن",                         105),
    ("ALMARAI",     "المراعي",                       106),
    ("BAHRI",       "البحري",                        107),
    ("ALINMA",      "مصرف الإنماء",                  108),
    ("TASI",        "المؤشر العام تاسي",             109),
    ("EMAAR",       "إعمار العقارية",                110),
    ("EMIRATESNBD", "بنك الإمارات دبي الوطني",       111),
    ("DIB",         "بنك دبي الإسلامي",              112),
    ("DFMGI",       "مؤشر سوق دبي المالي",           113),
    ("FAB",         "بنك أبوظبي الأول",              114),
    ("ADNOCDIST",   "أدنوك للتوزيع",                 115),
    ("QNBK",        "بنك قطر الوطني",                116),
]


def migrate():
    db = SessionLocal()
    added, skipped = 0, 0
    try:
        for symbol, display_name, sort_order in GULF_MARKETS:
            exists = db.query(MarketConfig).filter(MarketConfig.symbol == symbol).first()
            if exists:
                skipped += 1
                continue
            db.add(MarketConfig(
                symbol=symbol, display_name=display_name, category="gulf",
                is_active=True, is_premium=False,
                yf_symbol=None, td_symbol=None, sort_order=sort_order,
            ))
            added += 1
        db.commit()
        print(f"✅ Gulf markets migration done — added: {added}, already existed: {skipped}")
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
