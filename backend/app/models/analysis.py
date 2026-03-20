"""
Mosh AI Pro v5 - Analysis Model
Database model for storing detailed market analysis
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Analysis(Base):
    __tablename__ = "analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Signal Reference (optional - can be standalone analysis)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=True, unique=True)
    
    # Market Info
    market = Column(String, nullable=False, index=True)
    timeframe = Column(String, nullable=False)
    
    # Trend Analysis
    trend_direction = Column(String, nullable=True)  # BULLISH, BEARISH, RANGING
    trend_strength = Column(Float, nullable=True)  # 0-100
    market_structure = Column(JSON, nullable=True)  # HH, HL, LH, LL detection
    
    # Wyckoff Analysis
    wyckoff_phase = Column(String, nullable=True)  # Accumulation, Markup, Distribution, Markdown
    wyckoff_events = Column(JSON, nullable=True)  # Spring, Upthrust, Test, etc.
    wyckoff_confidence = Column(Float, nullable=True)
    
    # Liquidity Analysis
    equal_highs = Column(JSON, nullable=True)  # Array of equal high levels
    equal_lows = Column(JSON, nullable=True)  # Array of equal low levels
    liquidity_pools = Column(JSON, nullable=True)  # Detected liquidity zones
    liquidity_grabs = Column(JSON, nullable=True)  # Recent liquidity sweeps
    external_liquidity = Column(JSON, nullable=True)  # Major liquidity areas
    
    # Premium/Discount Zones
    premium_zone = Column(JSON, nullable=True)  # Upper 50% range
    discount_zone = Column(JSON, nullable=True)  # Lower 50% range
    current_zone = Column(String, nullable=True)  # PREMIUM, DISCOUNT, EQUILIBRIUM
    fibonacci_levels = Column(JSON, nullable=True)
    
    # Volume Intelligence
    volume_profile = Column(JSON, nullable=True)  # POC, VAH, VAL
    volume_delta = Column(Float, nullable=True)  # Buy vs Sell pressure
    volume_climax = Column(JSON, nullable=True)  # Climax detection
    volume_trend = Column(String, nullable=True)  # INCREASING, DECREASING, STABLE
    
    # BOS (Break of Structure) Analysis
    internal_bos = Column(JSON, nullable=True)  # Internal structure breaks
    external_bos = Column(JSON, nullable=True)  # External structure breaks
    choch = Column(JSON, nullable=True)  # Change of Character events
    bos_strength = Column(Float, nullable=True)
    
    # Order Blocks & Breaker Blocks
    order_blocks = Column(JSON, nullable=True)  # Bullish/Bearish OBs
    breaker_blocks = Column(JSON, nullable=True)  # Failed OBs turned BBs
    mitigation_blocks = Column(JSON, nullable=True)  # Mitigated zones
    rejection_blocks = Column(JSON, nullable=True)  # Strong rejection areas
    
    # Fair Value Gaps (FVG)
    fvg_bullish = Column(JSON, nullable=True)  # Bullish imbalances
    fvg_bearish = Column(JSON, nullable=True)  # Bearish imbalances
    fvg_strength = Column(Float, nullable=True)
    
    # Killzones Analysis
    current_killzone = Column(String, nullable=True)  # ASIA, LONDON, NEWYORK
    killzone_strength = Column(JSON, nullable=True)  # Strength per session
    optimal_entry_time = Column(String, nullable=True)
    
    # Time & Price Theory
    time_cycles = Column(JSON, nullable=True)  # Detected time cycles
    price_projections = Column(JSON, nullable=True)  # Price targets based on time
    harmonic_patterns = Column(JSON, nullable=True)  # Gartley, Butterfly, etc.
    
    # ATR & Volatility
    atr_value = Column(Float, nullable=True)
    volatility_level = Column(String, nullable=True)  # LOW, MEDIUM, HIGH, EXTREME
    volatility_analysis = Column(JSON, nullable=True)
    
    # AI Scoring
    overall_score = Column(Float, nullable=True)  # 0-100
    score_breakdown = Column(JSON, nullable=True)  # Individual component scores
    
    # Recommendations
    recommendation = Column(String, nullable=True)  # BUY, SELL, WAIT
    entry_zones = Column(JSON, nullable=True)  # Recommended entry areas
    invalidation_level = Column(Float, nullable=True)  # Analysis invalidation price
    
    # Raw Data
    raw_candles = Column(JSON, nullable=True)  # Candlestick data snapshot
    indicators = Column(JSON, nullable=True)  # Technical indicators
    
    # Metadata
    analysis_version = Column(String, default="5.0")  # AI Engine version
    processing_time_ms = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    signal = relationship("Signal", back_populates="analysis")
    
    def __repr__(self):
        return f"<Analysis(id={self.id}, market={self.market}, trend={self.trend_direction}, score={self.overall_score})>"
