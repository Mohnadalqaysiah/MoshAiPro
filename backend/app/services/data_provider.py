"""
Mosh AI Pro v5 - Data Provider
Handles data fetching from TwelveData and Finnhub APIs
"""

import requests
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import time
from loguru import logger
from app.config import get_settings

settings = get_settings()


INTERVAL_MAP = {
    "15m":  "15min",
    "30m":  "30min",
    "1h":   "1h",
    "4h":   "4h",
    "1d":   "1day",
    "1day": "1day",
    "1w":   "1week",
}

SYMBOL_MAP = {
    "XAUUSD": "XAU/USD",
    "BTCUSD": "BTC/USD",
    "EURUSD": "EUR/USD",
    "GBPUSD": "GBP/USD",
    "USDJPY": "USD/JPY",
    "USDCHF": "USD/CHF",
    "ETHUSD": "ETH/USD",
}

MARKET_HOURS = {
    "XAUUSD": True,   # Forex/Gold: closed weekends
    "EURUSD": True,
    "GBPUSD": True,
    "USDJPY": True,
    "USDCHF": True,
    "BTCUSD": False,  # Crypto: always open
    "ETHUSD": False,
}


class DataProvider:
    """Unified data provider for market data"""

    def __init__(self):
        self.twelvedata_key = settings.TWELVEDATA_API_KEY
        self.finnhub_key = settings.FINNHUB_API_KEY
        self.twelvedata_base = "https://api.twelvedata.com"
        self.finnhub_base = "https://finnhub.io/api/v1"
        self.cache = {}
        self.last_request_time = 0
        self.min_request_interval = 60 / settings.TWELVEDATA_RATE_LIMIT

    def _normalize_symbol(self, symbol: str) -> str:
        """Convert symbol to TwelveData format"""
        return SYMBOL_MAP.get(symbol.upper(), symbol)

    def _normalize_interval(self, interval: str) -> str:
        """Convert interval to TwelveData format"""
        return INTERVAL_MAP.get(interval.lower(), interval)

    def is_market_open(self, symbol: str) -> bool:
        """Check if market is currently open (weekday check for Forex)"""
        is_forex = MARKET_HOURS.get(symbol.upper(), True)
        if not is_forex:
            return True  # Crypto is always open
        now = datetime.utcnow()
        # Forex closed on weekends (Saturday=5, Sunday=6)
        if now.weekday() >= 5:
            return False
        return True
    
    def _rate_limit(self):
        """Ensure rate limiting compliance"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def get_market_data(
        self,
        symbol: str,
        interval: str = "1h",
        outputsize: int = 100
    ) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV data from TwelveData
        
        Args:
            symbol: Market symbol (e.g., 'XAU/USD', 'BTC/USD')
            interval: Timeframe (1min, 5min, 15min, 30min, 1h, 4h, 1day)
            outputsize: Number of candles to fetch
        
        Returns:
            DataFrame with columns: datetime, open, high, low, close, volume
        """
        normalized = self._normalize_symbol(symbol)
        norm_interval = self._normalize_interval(interval)
        cache_key = f"{normalized}_{norm_interval}_{outputsize}"

        # Check cache (5 minutes expiry)
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if (datetime.now() - cached_time).seconds < 300:
                logger.info(f"📦 Using cached data for {normalized}")
                return cached_data

        try:
            self._rate_limit()

            url = f"{self.twelvedata_base}/time_series"
            params = {
                "symbol": normalized,
                "interval": norm_interval,
                "outputsize": outputsize,
                "apikey": self.twelvedata_key,
                "format": "JSON"
            }
            
            logger.info(f"📡 Fetching {symbol} data from TwelveData...")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if "values" not in data:
                logger.error(f"❌ No data returned for {symbol}: {data}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(data["values"])
            df["datetime"] = pd.to_datetime(df["datetime"])
            df = df.sort_values("datetime").reset_index(drop=True)

            # Convert to numeric (volume is optional for crypto/forex)
            for col in ["open", "high", "low", "close"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            if "volume" in df.columns:
                df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
            else:
                df["volume"] = 0.0
            
            # Cache the data
            self.cache[cache_key] = (df, datetime.now())
            
            logger.success(f"✅ Fetched {len(df)} candles for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"❌ Error fetching data for {symbol}: {e}")
            return None
    
    def get_multi_timeframe_data(
        self,
        symbol: str,
        timeframes: List[str] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch data for multiple timeframes
        
        Args:
            symbol: Market symbol
            timeframes: List of timeframes (default: ['1day', '1h', '15min'])
        
        Returns:
            Dictionary mapping timeframe to DataFrame
        """
        if timeframes is None:
            timeframes = ['1day', '1h', '15min']
        
        result = {}
        for tf in timeframes:
            outputsize = 100 if tf != '1day' else 30
            df = self.get_market_data(symbol, tf, outputsize)
            if df is not None:
                result[tf] = df
        
        return result
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current real-time price
        
        Args:
            symbol: Market symbol
        
        Returns:
            Current price as float
        """
        try:
            self._rate_limit()
            
            url = f"{self.twelvedata_base}/price"
            params = {
                "symbol": symbol,
                "apikey": self.twelvedata_key
            }
            
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            
            if "price" in data:
                return float(data["price"])
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error fetching current price for {symbol}: {e}")
            return None
    
    def get_quote(self, symbol: str) -> Optional[Dict]:
        """
        Get detailed quote information
        
        Args:
            symbol: Market symbol
        
        Returns:
            Dictionary with quote data
        """
        try:
            self._rate_limit()
            
            url = f"{self.twelvedata_base}/quote"
            params = {
                "symbol": symbol,
                "apikey": self.twelvedata_key
            }
            
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"❌ Error fetching quote for {symbol}: {e}")
            return None
    
    def get_volume_data_finnhub(self, symbol: str) -> Optional[Dict]:
        """
        Get volume data from Finnhub (for crypto/stocks)
        Note: Finnhub has better volume data for some assets
        
        Args:
            symbol: Market symbol (adjust format for Finnhub)
        
        Returns:
            Volume analysis data
        """
        try:
            # Convert symbol format for Finnhub
            finnhub_symbol = self._convert_to_finnhub_symbol(symbol)
            
            url = f"{self.finnhub_base}/stock/candle"
            params = {
                "symbol": finnhub_symbol,
                "resolution": "60",  # 1 hour
                "from": int((datetime.now() - timedelta(days=7)).timestamp()),
                "to": int(datetime.now().timestamp()),
                "token": self.finnhub_key
            }
            
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("s") == "ok":
                return {
                    "volume": data.get("v", []),
                    "timestamp": data.get("t", []),
                    "close": data.get("c", [])
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"⚠️ Finnhub volume data not available for {symbol}: {e}")
            return None
    
    def _convert_to_finnhub_symbol(self, symbol: str) -> str:
        """Convert TwelveData symbol format to Finnhub format"""
        conversions = {
            "BTC/USD": "BINANCE:BTCUSDT",
            "BTCUSD": "BINANCE:BTCUSDT",
            "ETH/USD": "BINANCE:ETHUSDT",
            "ETHUSD": "BINANCE:ETHUSDT"
        }
        return conversions.get(symbol, symbol)
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range
        
        Args:
            df: DataFrame with high, low, close
            period: ATR period
        
        Returns:
            Series with ATR values
        """
        high = df["high"]
        low = df["low"]
        close = df["close"]
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    def detect_market_hours(self) -> Dict[str, bool]:
        """
        Detect which trading session is currently active
        
        Returns:
            Dictionary with session status
        """
        now = datetime.utcnow()
        hour = now.hour
        
        return {
            "asia": 0 <= hour < 8,
            "london": 8 <= hour < 16,
            "new_york": 13 <= hour < 22,
            "overlap_london_ny": 13 <= hour < 16
        }


# Singleton instance
data_provider = DataProvider()
