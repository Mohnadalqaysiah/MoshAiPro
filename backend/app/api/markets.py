"""
Qaffel AI - Markets API Routes
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from loguru import logger

from app.config import get_settings, MARKET_CONFIG
from app.database import get_db
from app.models.market_config import MarketConfig
from app.models.signal import Signal, SignalStatus
from app.services.auth_service import get_current_user
from app.services.smart_data import smart_data

settings = get_settings()
router = APIRouter()

# Fallback static data for markets not yet in DB
_STATIC_EXTRAS = {
    "NAS100":  {"name": "Nasdaq 100",       "name_ar": "ناسداك 100",     "category": "commodity", "yf_symbol": "NQ=F"},
    "SP500":   {"name": "S&P 500",          "name_ar": "إس آند بي 500",  "category": "commodity", "yf_symbol": "ES=F"},
    "US30":    {"name": "Dow Jones",         "name_ar": "داو جونز",       "category": "commodity", "yf_symbol": "YM=F"},
    "USOIL":   {"name": "Crude Oil WTI",    "name_ar": "النفط الخام",     "category": "commodity", "yf_symbol": "CL=F"},
    "XAGUSD":  {"name": "Silver",           "name_ar": "الفضة",           "category": "commodity", "yf_symbol": "SI=F"},
    "NATGAS":  {"name": "Natural Gas",      "name_ar": "الغاز الطبيعي",  "category": "commodity", "yf_symbol": "NG=F"},
    "ETHUSD":  {"name": "Ethereum",         "name_ar": "إيثريوم",         "category": "crypto",    "yf_symbol": "ETH-USD"},
    "AAPL":    {"name": "Apple Inc",        "name_ar": "أبل",             "category": "stock",     "yf_symbol": "AAPL"},
    "TSLA":    {"name": "Tesla",            "name_ar": "تيسلا",            "category": "stock",     "yf_symbol": "TSLA"},
    "NVDA":    {"name": "Nvidia",           "name_ar": "نفيديا",          "category": "stock",     "yf_symbol": "NVDA"},
    "MSFT":    {"name": "Microsoft",        "name_ar": "مايكروسوفت",      "category": "stock",     "yf_symbol": "MSFT"},
    "GOOGL":   {"name": "Alphabet (Google)","name_ar": "جوجل",            "category": "stock",     "yf_symbol": "GOOGL"},
    "META":    {"name": "Meta Platforms",   "name_ar": "ميتا",            "category": "stock",     "yf_symbol": "META"},
    "AMZN":    {"name": "Amazon",           "name_ar": "أمازون",          "category": "stock",     "yf_symbol": "AMZN"},
}


@router.get("/list")
def get_supported_markets(db: Session = Depends(get_db)):
    """
    يرجع الأزواج النشطة من جدول market_configs.
    إذا كان الجدول فارغاً يرجع الأزواج الافتراضية.
    """
    try:
        db_markets = db.query(MarketConfig).filter(
            MarketConfig.is_active == True
        ).order_by(MarketConfig.sort_order, MarketConfig.symbol).all()

        if db_markets:
            return {
                "success": True,
                "count": len(db_markets),
                "data": [
                    {
                        "symbol":    m.symbol,
                        "name":      m.display_name,
                        "name_ar":   m.display_name,
                        "category":  m.category or "forex",
                        "yf_symbol": m.yf_symbol,
                        "is_premium":m.is_premium,
                    }
                    for m in db_markets
                ],
            }

        # fallback: static config + extras
        markets = []
        for symbol, cfg in MARKET_CONFIG.items():
            markets.append({
                "symbol":    symbol,
                "name":      cfg["name"],
                "name_ar":   cfg.get("name_ar", cfg["name"]),
                "category":  "forex",
                "yf_symbol": None,
                "is_premium":False,
            })
        for symbol, cfg in _STATIC_EXTRAS.items():
            if symbol not in MARKET_CONFIG:
                markets.append({
                    "symbol":    symbol,
                    "name":      cfg["name"],
                    "name_ar":   cfg["name_ar"],
                    "category":  cfg["category"],
                    "yf_symbol": cfg["yf_symbol"],
                    "is_premium":False,
                })
        return {"success": True, "count": len(markets), "data": markets}

    except Exception as e:
        logger.error(f"❌ Error fetching markets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/overview")
def market_overview(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Market Overview — خريطة حرارية لجميع الأسواق.
    يُرجع آخر إشارة لكل رمز (الاتجاه + الثقة) + إحصائيات الأداء.
    """
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import func

    closed = [SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.SL_HIT]
    since_30d = datetime.now(timezone.utc) - timedelta(days=30)

    # آخر إشارة لكل رمز (subquery: max id per market)
    sub = (
        db.query(Signal.market, func.max(Signal.id).label("max_id"))
        .group_by(Signal.market)
        .subquery()
    )
    latest_sigs = (
        db.query(Signal)
        .join(sub, Signal.id == sub.c.max_id)
        .all()
    )

    # Win-rate آخر 30 يوم لكل رمز
    perf_sigs = db.query(Signal).filter(
        Signal.status.in_(closed),
        Signal.created_at >= since_30d,
    ).all()

    perf: dict = {}
    for s in perf_sigs:
        m = s.market or "?"
        if m not in perf:
            perf[m] = {"wins": 0, "losses": 0}
        if s.status in (SignalStatus.TP1_HIT, SignalStatus.TP2_HIT):
            perf[m]["wins"] += 1
        else:
            perf[m]["losses"] += 1

    # Live prices
    try:
        from app.services.smart_data import smart_data
        def _price(sym):
            meta = smart_data.get_realtime_price_with_meta(sym)
            return round(meta["price"], 5) if meta else None
    except Exception:
        def _price(_): return None

    markets_map = {}
    for sig in latest_sigs:
        m  = sig.market or "?"
        p  = perf.get(m, {})
        res = p.get("wins", 0) + p.get("losses", 0)
        wr  = round(p["wins"] / res * 100) if res > 0 else None
        markets_map[m] = {
            "symbol":         m,
            "direction":      sig.signal_type or "WAIT",
            "confidence":     float(sig.ai_confidence or 0),
            "win_rate_30d":   wr,
            "wins_30d":       p.get("wins", 0),
            "losses_30d":     p.get("losses", 0),
            "last_signal_at": sig.created_at.isoformat() if sig.created_at else None,
            "live_price":     _price(m),
        }

    # أضف الأسواق التي لا توجد لها إشارات بعد
    try:
        for m in db.query(MarketConfig).filter(MarketConfig.is_active == True).all():
            if m.symbol not in markets_map:
                markets_map[m.symbol] = {
                    "symbol": m.symbol, "direction": "WAIT", "confidence": 0,
                    "win_rate_30d": None, "wins_30d": 0, "losses_30d": 0,
                    "last_signal_at": None, "live_price": _price(m.symbol),
                }
    except Exception:
        pass

    items = sorted(markets_map.values(), key=lambda x: (
        0 if x["direction"] in ("BUY", "SELL") else 1,
        -(x["confidence"] or 0),
    ))

    return {
        "markets": items,
        "summary": {
            "buy":  sum(1 for x in items if x["direction"] == "BUY"),
            "sell": sum(1 for x in items if x["direction"] == "SELL"),
            "wait": sum(1 for x in items if x["direction"] not in ("BUY","SELL")),
        },
        "total": len(items),
    }


@router.get("/{symbol}/price")
async def get_current_price(symbol: str):
    """
    Get current price for a market
    """
    try:
        price = await smart_data.get_current_price_async(symbol)
        
        if price is None:
            raise HTTPException(status_code=404, detail=f"Price not available for {symbol}")
        
        return {
            "success": True,
            "data": {
                "symbol": symbol,
                "price": price
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching price: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/candles")
async def get_market_candles(
    symbol: str,
    interval: str = "1h",
    limit: int = 100
):
    """
    Get candlestick data for a market
    """
    try:
        df = await smart_data.get_ohlcv(symbol, interval, bars=limit)
        
        if df is None:
            raise HTTPException(status_code=404, detail=f"Data not available for {symbol}")
        
        candles = []
        for _, row in df.iterrows():
            candles.append({
                "timestamp": row["datetime"].isoformat(),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"])
            })
        
        return {
            "success": True,
            "symbol": symbol,
            "interval": interval,
            "count": len(candles),
            "data": candles
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching candles: {e}")
        raise HTTPException(status_code=500, detail=str(e))
