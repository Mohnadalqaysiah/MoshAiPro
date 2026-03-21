"""
Mosh AI Pro v5 - Market Config Model
Admin controls which pairs are active
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float
from sqlalchemy.sql import func
from app.database import Base


class MarketConfig(Base):
    __tablename__ = "market_configs"

    id          = Column(Integer, primary_key=True, index=True)
    symbol      = Column(String, unique=True, index=True, nullable=False)  # XAUUSD
    display_name = Column(String, nullable=False)   # Gold / XAU/USD
    category    = Column(String, default="forex")   # forex / crypto / commodity
    is_active   = Column(Boolean, default=True)
    is_premium  = Column(Boolean, default=False)     # مدفوع فقط

    # TwelveData / yfinance symbol
    yf_symbol   = Column(String, nullable=True)      # GC=F
    td_symbol   = Column(String, nullable=True)      # XAU/USD

    sort_order  = Column(Integer, default=0)

    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())
