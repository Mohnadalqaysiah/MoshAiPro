"""
migrate_markets.py — بذر جدول market_configs بالأزواج الافتراضية
شغّل مرة واحدة:
  docker compose -f docker-compose.prod.yml exec backend python migrate_markets.py
"""
from app.database import engine, SessionLocal
from app.models.market_config import MarketConfig

DEFAULT_MARKETS = [
    # ─── Forex ────────────────────────────────────────────────────
    dict(symbol="XAUUSD", display_name="Gold / XAU/USD",          category="forex",     yf_symbol="GC=F",       td_symbol="XAU/USD",  sort_order=1),
    dict(symbol="BTCUSD", display_name="Bitcoin / BTC/USD",        category="crypto",    yf_symbol="BTC-USD",    td_symbol="BTC/USD",  sort_order=2),
    dict(symbol="EURUSD", display_name="Euro / EUR/USD",            category="forex",     yf_symbol="EURUSD=X",   td_symbol="EUR/USD",  sort_order=3),
    dict(symbol="GBPUSD", display_name="Pound / GBP/USD",           category="forex",     yf_symbol="GBPUSD=X",   td_symbol="GBP/USD",  sort_order=4),
    dict(symbol="USDJPY", display_name="Dollar / USD/JPY",          category="forex",     yf_symbol="USDJPY=X",   td_symbol="USD/JPY",  sort_order=5),
    dict(symbol="USDCHF", display_name="Franc / USD/CHF",           category="forex",     yf_symbol="USDCHF=X",   td_symbol="USD/CHF",  sort_order=6),
    # ─── Indices ──────────────────────────────────────────────────
    dict(symbol="NAS100", display_name="Nasdaq 100",                category="commodity", yf_symbol="NQ=F",       td_symbol="NAS100",   sort_order=10),
    dict(symbol="SP500",  display_name="S&P 500",                   category="commodity", yf_symbol="ES=F",       td_symbol="SPX500",   sort_order=11),
    dict(symbol="US30",   display_name="Dow Jones / US30",          category="commodity", yf_symbol="YM=F",       td_symbol="US30",     sort_order=12),
    # ─── Commodities ──────────────────────────────────────────────
    dict(symbol="USOIL",  display_name="Crude Oil WTI",             category="commodity", yf_symbol="CL=F",       td_symbol="WTI/USD",  sort_order=20),
    dict(symbol="XAGUSD", display_name="Silver / XAG/USD",          category="commodity", yf_symbol="SI=F",       td_symbol="XAG/USD",  sort_order=21),
    dict(symbol="NATGAS", display_name="Natural Gas",               category="commodity", yf_symbol="NG=F",       td_symbol="NATGAS",   sort_order=22),
    # ─── Crypto ───────────────────────────────────────────────────
    dict(symbol="ETHUSD", display_name="Ethereum / ETH/USD",        category="crypto",    yf_symbol="ETH-USD",    td_symbol="ETH/USD",  sort_order=30),
    # ─── Stocks ───────────────────────────────────────────────────
    dict(symbol="AAPL",   display_name="Apple Inc (AAPL)",          category="stock",     yf_symbol="AAPL",       td_symbol="AAPL",     sort_order=40),
    dict(symbol="TSLA",   display_name="Tesla (TSLA)",              category="stock",     yf_symbol="TSLA",       td_symbol="TSLA",     sort_order=41),
    dict(symbol="NVDA",   display_name="Nvidia (NVDA)",             category="stock",     yf_symbol="NVDA",       td_symbol="NVDA",     sort_order=42),
    dict(symbol="MSFT",   display_name="Microsoft (MSFT)",          category="stock",     yf_symbol="MSFT",       td_symbol="MSFT",     sort_order=43),
    dict(symbol="GOOGL",  display_name="Alphabet Google (GOOGL)",   category="stock",     yf_symbol="GOOGL",      td_symbol="GOOGL",    sort_order=44),
    dict(symbol="META",   display_name="Meta Platforms (META)",     category="stock",     yf_symbol="META",       td_symbol="META",     sort_order=45),
    dict(symbol="AMZN",   display_name="Amazon (AMZN)",             category="stock",     yf_symbol="AMZN",       td_symbol="AMZN",     sort_order=46),
]

def run():
    db = SessionLocal()
    added = 0
    try:
        for m in DEFAULT_MARKETS:
            existing = db.query(MarketConfig).filter(MarketConfig.symbol == m["symbol"]).first()
            if not existing:
                db.add(MarketConfig(**m, is_active=True, is_premium=False))
                added += 1
                print(f"✅ أُضيف: {m['symbol']}")
            else:
                # تحديث yf_symbol و td_symbol إذا كانا فارغين
                changed = False
                if not existing.yf_symbol and m.get("yf_symbol"):
                    existing.yf_symbol = m["yf_symbol"]; changed = True
                if not existing.td_symbol and m.get("td_symbol"):
                    existing.td_symbol = m["td_symbol"]; changed = True
                if not existing.category and m.get("category"):
                    existing.category = m["category"]; changed = True
                if changed:
                    print(f"🔄 تحديث: {m['symbol']}")
        db.commit()
        print(f"\n🎉 انتهى — {added} زوج جديد أُضيف")
    finally:
        db.close()

if __name__ == "__main__":
    run()
