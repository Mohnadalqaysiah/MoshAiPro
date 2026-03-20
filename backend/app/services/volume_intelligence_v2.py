"""
Mosh AI Pro v5 - Volume Intelligence Engine v2
Advanced volume analysis: Volume Profile, Delta, Climax, Trends
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from loguru import logger


class VolumeIntelligenceV2:
    """
    Advanced volume analysis including:
    - Volume Profile (POC, VAH, VAL)
    - Volume Delta (Buy vs Sell pressure)
    - Volume Climax (Exhaustion points)
    - Volume Trend Analysis
    """
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """Perform comprehensive volume analysis"""
        
        if df is None or len(df) < 30:
            return self._empty_result()
        
        try:
            # Volume trend
            volume_trend = self._analyze_volume_trend(df)
            
            # Volume delta (if available - requires tick data)
            volume_delta = self._calculate_volume_delta(df)
            
            # Volume climax detection
            volume_climax = self._detect_volume_climax(df)
            
            # Volume strength
            volume_strength = self._calculate_volume_strength(df)
            
            # Volume profile (simplified)
            volume_profile = self._calculate_volume_profile(df)
            
            result = {
                "volume_trend": volume_trend,
                "volume_delta": volume_delta,
                "volume_climax": volume_climax,
                "volume_strength": volume_strength,
                "volume_profile": volume_profile,
                "confidence": 75.0
            }
            
            logger.info(f"📊 Volume: {volume_trend} trend, Strength: {volume_strength}%")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in Volume analysis: {e}")
            return self._empty_result()
    
    def _analyze_volume_trend(self, df: pd.DataFrame) -> str:
        """Analyze if volume is increasing, decreasing, or stable"""
        
        recent_volume = df["volume"].tail(20).mean()
        older_volume = df["volume"].tail(50).head(30).mean()
        
        if older_volume == 0:
            return "STABLE"
        
        change = (recent_volume - older_volume) / older_volume
        
        if change > 0.2:
            return "INCREASING"
        elif change < -0.2:
            return "DECREASING"
        else:
            return "STABLE"
    
    def _calculate_volume_delta(self, df: pd.DataFrame) -> Dict:
        """
        Estimate volume delta (buying vs selling pressure)
        Note: True delta requires tick data - this is an approximation
        """
        
        recent = df.tail(20)
        
        # Approximate: green candles = buying, red = selling
        bullish_volume = recent[recent["close"] > recent["open"]]["volume"].sum()
        bearish_volume = recent[recent["close"] < recent["open"]]["volume"].sum()
        
        total = bullish_volume + bearish_volume
        
        if total == 0:
            return {"delta": 0, "bias": "NEUTRAL"}
        
        delta = (bullish_volume - bearish_volume) / total
        
        if delta > 0.2:
            bias = "BULLISH"
        elif delta < -0.2:
            bias = "BEARISH"
        else:
            bias = "NEUTRAL"
        
        return {
            "delta": float(delta),
            "bias": bias,
            "bullish_volume": float(bullish_volume),
            "bearish_volume": float(bearish_volume)
        }
    
    def _detect_volume_climax(self, df: pd.DataFrame) -> Dict:
        """
        Detect volume climax (extremely high volume indicating potential reversal)
        """
        
        avg_volume = df["volume"].tail(50).mean()
        std_volume = df["volume"].tail(50).std()
        
        recent_volume = df["volume"].tail(5)
        
        # Check for volume spike
        climax_detected = any(v > (avg_volume + 2 * std_volume) for v in recent_volume)
        
        if climax_detected:
            last_candle = df.iloc[-1]
            direction = "BULLISH" if last_candle["close"] > last_candle["open"] else "BEARISH"
            
            return {
                "detected": True,
                "direction": direction,
                "significance": "HIGH",
                "description": f"{direction} climax - potential exhaustion"
            }
        
        return {
            "detected": False,
            "direction": "NONE",
            "significance": "NONE",
            "description": "No climax detected"
        }
    
    def _calculate_volume_strength(self, df: pd.DataFrame) -> float:
        """Calculate overall volume strength (0-100)"""
        
        avg_volume = df["volume"].tail(50).mean()
        current_volume = df["volume"].tail(10).mean()
        
        if avg_volume == 0:
            return 50.0
        
        ratio = current_volume / avg_volume
        
        # Convert to 0-100 scale
        strength = min(ratio * 50, 100)
        
        return round(strength, 2)
    
    def _calculate_volume_profile(self, df: pd.DataFrame) -> Dict:
        """
        Simplified volume profile calculation
        Real implementation would need tick/depth data
        """
        
        recent = df.tail(100)
        
        # Approximate POC (Point of Control - price with most volume)
        price_levels = {}
        
        for _, row in recent.iterrows():
            price_level = round(row["close"], 2)
            if price_level not in price_levels:
                price_levels[price_level] = 0
            price_levels[price_level] += row["volume"]
        
        if not price_levels:
            return {}
        
        poc_price = max(price_levels, key=price_levels.get)
        
        return {
            "poc": float(poc_price),
            "description": "Point of Control - highest volume price"
        }
    
    def _empty_result(self) -> Dict:
        """Return empty result"""
        return {
            "volume_trend": "UNKNOWN",
            "volume_delta": {},
            "volume_climax": {},
            "volume_strength": 0,
            "volume_profile": {},
            "confidence": 0
        }


# Singleton instance
volume_intelligence_v2 = VolumeIntelligenceV2()
