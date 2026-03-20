"""
Mosh AI Pro v5 - Markets API Routes
"""

from fastapi import APIRouter, HTTPException
from loguru import logger

from app.config import get_settings, MARKET_CONFIG
from app.services.data_provider import data_provider

settings = get_settings()
router = APIRouter()


@router.get("/list")
async def get_supported_markets():
    """
    Get list of supported markets
    """
    try:
        markets = []
        
        for symbol, config in MARKET_CONFIG.items():
            markets.append({
                "symbol": symbol,
                "name": config["name"],
                "name_ar": config["name_ar"],
                "display": config["symbol"],
                "tick_size": config["tick_size"]
            })
        
        return {
            "success": True,
            "count": len(markets),
            "data": markets
        }
    
    except Exception as e:
        logger.error(f"❌ Error fetching markets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/price")
async def get_current_price(symbol: str):
    """
    Get current price for a market
    """
    try:
        price = data_provider.get_current_price(symbol)
        
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
        df = data_provider.get_market_data(symbol, interval, limit)
        
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
