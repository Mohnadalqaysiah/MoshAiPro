"""
migrate_add_expanded_markets.py
يضيف 16 رمز جديد إلى market_configs — فوركس متقاطع، كريبتو إضافي،
معادن إضافية، وسهمين أمريكيين كانا ممپوطين بـsmart_data.py بدون تفعيل.
كل الرموز ممپوطة أصلاً بـYFINANCE_MAP (smart_data.py) بنفس نمط الرموز
الشغّالة حالياً — راجع SIGNALS_STRATEGY.md وتحليل توسيع الرموز 2026-08-30.

Run: docker exec moshapi_backend python /app/migrate_add_expanded_markets.py
"""
import sys
sys.path.insert(0, "/app")
from app.database import SessionLocal
from app.models.market_config import MarketConfig
from app.models import user, payment, signal, analysis_log, affiliate, price_alert, strategy  # noqa: F401

# (symbol, display_name, category, yf_symbol, td_symbol, sort_order)
NEW_MARKETS = [
    # فوركس — أزواج رئيسية إضافية + متقاطعة
    ("AUDUSD",  "Australian Dollar / AUD/USD", "forex", "AUDUSD=X", "AUD/USD", 7),
    ("USDCAD",  "Canadian Dollar / USD/CAD",    "forex", "USDCAD=X", "USD/CAD", 8),
    ("NZDUSD",  "New Zealand Dollar / NZD/USD", "forex", "NZDUSD=X", "NZD/USD", 9),
    ("EURGBP",  "Euro/Pound / EUR/GBP",         "forex", "EURGBP=X", "EUR/GBP", 10),
    ("EURJPY",  "Euro/Yen / EUR/JPY",           "forex", "EURJPY=X", "EUR/JPY", 11),
    ("GBPJPY",  "Pound/Yen / GBP/JPY",          "forex", "GBPJPY=X", "GBP/JPY", 12),
    ("DXY",     "US Dollar Index / DXY",        "forex", "DX-Y.NYB", None, 13),

    # معادن إضافية
    ("COPPER",  "Copper",                       "commodity", "HG=F", None, 23),
    ("XPTUSD",  "Platinum / XPT/USD",            "commodity", "PL=F", None, 24),

    # كريبتو إضافي
    ("BNBUSD",  "Binance Coin / BNB/USD",  "crypto", "BNB-USD",  "BNB/USD", 31),
    ("SOLUSD",  "Solana / SOL/USD",        "crypto", "SOL-USD",  "SOL/USD", 32),
    ("XRPUSD",  "Ripple / XRP/USD",        "crypto", "XRP-USD",  "XRP/USD", 33),
    ("ADAUSD",  "Cardano / ADA/USD",       "crypto", "ADA-USD",  "ADA/USD", 34),
    ("DOGEUSD", "Dogecoin / DOGE/USD",     "crypto", "DOGE-USD", "DOGE/USD", 35),

    # أسهم أمريكية — كانت ممپوطة بـYFINANCE_MAP بدون تفعيل
    ("AMD",  "AMD Inc (AMD)",   "stock", "AMD",  "AMD", 47),
    ("NFLX", "Netflix (NFLX)",  "stock", "NFLX", "NFLX", 48),
]


def migrate():
    db = SessionLocal()
    added, skipped = 0, 0
    try:
        for symbol, display_name, category, yf_symbol, td_symbol, sort_order in NEW_MARKETS:
            exists = db.query(MarketConfig).filter(MarketConfig.symbol == symbol).first()
            if exists:
                skipped += 1
                continue
            db.add(MarketConfig(
                symbol=symbol, display_name=display_name, category=category,
                is_active=True, is_premium=False,
                yf_symbol=yf_symbol, td_symbol=td_symbol, sort_order=sort_order,
            ))
            added += 1
        db.commit()
        print(f"✅ Expanded markets migration done — added: {added}, already existed: {skipped}")
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
