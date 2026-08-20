"""
Mosh AI Pro v5 - Configuration Management
Handles all application settings and environment variables
"""

from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """Application Settings"""
    
    # ----- Database -----
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    
    # ----- API Keys -----
    TWELVEDATA_API_KEY: str
    FINNHUB_API_KEY: str
    TELEGRAM_BOT_TOKEN: str
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    
    # ----- Security -----
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200
    
    # ----- Application -----
    APP_NAME: str = "Qaffel AI Trade"
    APP_VERSION: str = "5.2.0"
    DEBUG: bool = True
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    
    # ----- Trading -----
    ANALYSIS_INTERVAL_MINUTES: int = 15
    SUPPORTED_MARKETS: str = "XAUUSD,BTCUSD,EURUSD,USDJPY,GBPUSD,USDCHF"
    DEFAULT_MARKET: str = "XAUUSD"
    DEFAULT_TIMEFRAME: str = "1h"
    
    # ----- AI Engine -----
    AI_CONFIDENCE_THRESHOLD: int = 60
    PREMIUM_CONFIDENCE_THRESHOLD: int = 80
    ENABLE_WYCKOFF_ANALYSIS: bool = True
    ENABLE_LIQUIDITY_ENGINE: bool = True
    ENABLE_VOLUME_INTELLIGENCE: bool = True
    ENABLE_KILLZONES: bool = True
    ENABLE_PREMIUM_DISCOUNT: bool = True
    ENABLE_BREAKER_BLOCKS: bool = True
    ENABLE_TIME_PRICE_THEORY: bool = True
    
    # ----- Risk Management -----
    DEFAULT_RISK_PERCENTAGE: float = 2.0
    MAX_RISK_PERCENTAGE: float = 5.0
    ATR_MULTIPLIER_SL: float = 1.5
    ATR_MULTIPLIER_TP1: float = 2.0
    ATR_MULTIPLIER_TP2: float = 3.5
    
    # ----- Telegram -----
    TELEGRAM_ADMIN_IDS: str = ""
    ADMIN_TELEGRAM_ID: str = ""   # Numeric chat ID for @Mgaisi admin notifications
    TRIAL_PERIOD_DAYS: int = 7
    MAX_SIGNALS_PER_DAY: int = 10
    
    # ----- WebSocket -----
    WEBSOCKET_HEARTBEAT_INTERVAL: int = 30
    WEBSOCKET_MAX_CONNECTIONS: int = 100
    
    # ----- Logging -----
    LOG_LEVEL: str = "INFO"
    LOG_FILE_PATH: str = "/var/log/mosh-ai-pro/app.log"
    
    # ----- Redis -----
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_EXPIRATION_SECONDS: int = 300
    
    # ----- Rate Limits -----
    TWELVEDATA_RATE_LIMIT: int = 8
    FINNHUB_RATE_LIMIT: int = 60

    # ----- Email / SMTP (Hostinger SSL) -----
    SMTP_HOST: str = "smtp.hostinger.com"
    SMTP_PORT: int = 465
    SMTP_USER: str = "support@qaffel.com"
    SMTP_PASSWORD: str = ""
    SMTP_FROM_NAME: str = "Qaffel AI"
    SUPPORT_EMAIL: str = "support@qaffel.com"

    # ----- SaaS / Payments -----
    TELEGRAM_BOT_USERNAME: str = "Qaffelbot"
    BOT_SECRET: str = "mosh-bot-secret-change-me"
    USDT_WALLET_ADDRESS: str = "TVh8P92EEjr732frVRpxg1iE4GsfZpLM6E"
    USDT_NETWORK: str = "TRC20"
    TRIAL_ANALYSES: int = 10
    TRIAL_CHAT: int = 20
    TRIAL_DAYS: int = 7

    # ----- Stripe -----
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_SUCCESS_URL: str = "https://qaffel.com/dashboard?stripe=success"
    STRIPE_CANCEL_URL: str = "https://qaffel.com/pricing?stripe=cancel"

    # ----- Spaceremit -----
    SPACEREMIT_PUBLIC_KEY: str = ""
    SPACEREMIT_SECRET_KEY: str = ""
    SPACEREMIT_TEST_PUBLIC_KEY: str = ""
    SPACEREMIT_TEST_SECRET_KEY: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def get_allowed_origins(self) -> List[str]:
        """Parse CORS allowed origins"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    def get_supported_markets(self) -> List[str]:
        """Get list of supported trading markets"""
        return [market.strip() for market in self.SUPPORTED_MARKETS.split(",")]
    
    def get_admin_ids(self) -> List[int]:
        """Get list of Telegram admin IDs"""
        if not self.TELEGRAM_ADMIN_IDS:
            return []
        return [int(id.strip()) for id in self.TELEGRAM_ADMIN_IDS.split(",")]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Market Configuration
MARKET_CONFIG = {
    "XAUUSD": {
        "name": "Gold",
        "name_ar": "الذهب",
        "symbol": "XAU/USD",
        "tick_size": 0.01,
        "min_move": 0.1,
        "session_times": {
            "asia": {"start": "00:00", "end": "08:00"},
            "london": {"start": "08:00", "end": "16:00"},
            "new_york": {"start": "13:00", "end": "22:00"}
        }
    },
    "BTCUSD": {
        "name": "Bitcoin",
        "name_ar": "البيتكوين",
        "symbol": "BTC/USD",
        "tick_size": 1.0,
        "min_move": 10,
        "session_times": {
            "asia": {"start": "00:00", "end": "08:00"},
            "london": {"start": "08:00", "end": "16:00"},
            "new_york": {"start": "13:00", "end": "22:00"}
        }
    },
    "EURUSD": {
        "name": "Euro/US Dollar",
        "name_ar": "اليورو/الدولار",
        "symbol": "EUR/USD",
        "tick_size": 0.00001,
        "min_move": 0.0001,
        "session_times": {
            "asia": {"start": "00:00", "end": "08:00"},
            "london": {"start": "08:00", "end": "16:00"},
            "new_york": {"start": "13:00", "end": "22:00"}
        }
    },
    "USDJPY": {
        "name": "US Dollar/Japanese Yen",
        "name_ar": "الدولار/الين",
        "symbol": "USD/JPY",
        "tick_size": 0.001,
        "min_move": 0.01,
        "session_times": {
            "asia": {"start": "00:00", "end": "08:00"},
            "london": {"start": "08:00", "end": "16:00"},
            "new_york": {"start": "13:00", "end": "22:00"}
        }
    },
    "GBPUSD": {
        "name": "British Pound/US Dollar",
        "name_ar": "الجنيه/الدولار",
        "symbol": "GBP/USD",
        "tick_size": 0.00001,
        "min_move": 0.0001,
        "session_times": {
            "asia": {"start": "00:00", "end": "08:00"},
            "london": {"start": "08:00", "end": "16:00"},
            "new_york": {"start": "13:00", "end": "22:00"}
        }
    },
    "USDCHF": {
        "name": "US Dollar/Swiss Franc",
        "name_ar": "الدولار/الفرنك",
        "symbol": "USD/CHF",
        "tick_size": 0.00001,
        "min_move": 0.0001,
        "session_times": {
            "asia": {"start": "00:00", "end": "08:00"},
            "london": {"start": "08:00", "end": "16:00"},
            "new_york": {"start": "13:00", "end": "22:00"}
        }
    }
}


# Timeframe Configuration
TIMEFRAME_CONFIG = {
    "1m": {"minutes": 1, "candles_needed": 500},
    "5m": {"minutes": 5, "candles_needed": 300},
    "15m": {"minutes": 15, "candles_needed": 200},
    "30m": {"minutes": 30, "candles_needed": 150},
    "1h": {"minutes": 60, "candles_needed": 100},
    "4h": {"minutes": 240, "candles_needed": 60},
    "1day": {"minutes": 1440, "candles_needed": 30}
}


# Signal Types
SIGNAL_TYPES = {
    "BUY": {"emoji": "🟢", "color": "#10b981", "ar": "شراء"},
    "SELL": {"emoji": "🔴", "color": "#ef4444", "ar": "بيع"},
    "WATCH": {"emoji": "⚪", "color": "#6b7280", "ar": "مراقبة"}
}


# Signal Status
SIGNAL_STATUS = {
    "PENDING": {"emoji": "⏳", "ar": "قيد الانتظار"},
    "ACTIVE": {"emoji": "🔵", "ar": "نشط"},
    "TP1_HIT": {"emoji": "🎯", "ar": "هدف أول"},
    "TP2_HIT": {"emoji": "🏆", "ar": "هدف ثاني"},
    "SL_HIT": {"emoji": "❌", "ar": "وقف خسارة"},
    "EXPIRED": {"emoji": "⌛", "ar": "منتهي"}
}
